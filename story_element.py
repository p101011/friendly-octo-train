import uuid

class State:
    def __init__(self, name, value, timestep):
        self.name = name
        self.value = value
        self.t = timestep

    def __eq__(self, other):
        return self.value == other.value

class History:
    def __init__(self):
        self.actions = []
        self.unique_elements = set()
        self.last_added_element = -1

    def add_action(self, action, t):
        self.actions.append(action)
        for el in action.elements:
            if el.uuid not in self.unique_elements:
                self.unique_elements.add(el)
                self.last_added_element = action.t
        action.apply(t)

    def contains_element(self, element):
        query_id = element.uuid
        for e in self.unique_elements:
            if query_id == e.uuid:
                return True
        return False

    # takes a tentative action and sees if we can map the elements within to existing elements
    # returns a new action with aligned elements
    def map_elements(self, action):
        # takes an element and compares against elements within history
        # returns given element or a new element it can be mapped into
        def map_element(element):
            for e0 in self.unique_elements:
                if element.uuid == e0.uuid:
                    # we already have this element in our history, no need to map
                    return element
                if element.name != e0.name:
                    # there are interesting cases here where the same object could have different names
                    # for simplicity, we'll ignore those
                    return element
                if element.state_history["location"] != e0.state_history["location"]:
                    # these elements are in different locations, so can't be the same
                    return element
                element_parent = element.state_history["parent"][-1]
                if element_parent is not None and e0.state_history["parent"][-1] != element_parent:
                    # our element has a known parent and it is different from the other's
                    return element

                # our two elements match in all significant fields, so element can be mapped to e0
                return e0

        init = map_element(action.initiator)
        receivers = [map_element(e) for e in action.receivers]
        return Action(action.name, init, receivers)

class StoryElement:
    def __init__(self, token, init_state=None, descriptors=None):
        self.token = token
        self.name = self.token.lower_
        self.state_history = {
            "location": [],
            "parent": [],
            "extant": []
        }
        if init_state is not None:
            for key in init_state:
                if key in self.state_history:
                    self.state_history[key].append(init_state[key])
                else:
                    self.state_history[key] = [init_state[key]]
        self.descriptors = descriptors
        self.action_history = []
        self.uuid = uuid.uuid4()

    def __str__(self):
        if not any(self.descriptors):
            return self.name
        return '{} {}'.format(' '.join([x.lower_ for x in self.descriptors]), self.name)

    def __repr__(self):
        return str(self)

class Action:
    def __init__(self, name, e0, e1):
        self.name = name
        self.initiators = e0
        self.receivers = e1
        self.elements = e0.copy()
        for obj_type in self.receivers:
            self.elements += self.receivers[obj_type]
        self.t = -1
        self.uuid = uuid.uuid4()

    # validates this action against a history
    # returns false if the action would break common rules (i.e. can't kill dead person)
    def validate(self, reject_incomplete):
        # check to ensure that all elements involved in action currently exist
        for el in self.elements:
            if any(el.state_history['extant']):
                last_state = el.state_history['extant'][-1]
                if last_state.value is False:
                    return False
        return True

    # concretely applies this action to the objects contained
    def apply(self, t):
        self.t = t
        for e in self.elements:
            e.action_history.append((self, self.t))

    def __str__(self):
        obj_str = ', '.join([str(obj) + ' {}'.format(x) for x in self.receivers for obj in self.receivers[x]])
        return "{} - {} - {}".format(', '.join([str(x) for x in self.initiators]), self.name, obj_str)

    def __repr__(self):
        return str(self)

    # consider two cases: in one, the subject(s) is/are also the object(s)
    # in second, subject(s) and object(s) are distinct
    def get_action_targets(self):
        # have to check for direct or indirect objects, then default to the subject
        for obj_type in self.receivers:
            if any(self.receivers[obj_type]):
                return self.receivers
        return self.initiators


class MoveAction(Action):
    def __init__(self, name, e0, e1):
        super().__init__(name, e0, e1)

    def validate(self, reject_incomplete):
        super().validate(reject_incomplete)
        move_targets = self.get_action_targets()
        if isinstance(move_targets, dict):
            # might be subject, a.k.a. self.initiators
            move_targets = move_targets["direct"]
        for target in move_targets:
            target_movement_states = [x for x in target.state_history["location"] if x.name == 'emplace']
            if any(target_movement_states):
                last_state = target_movement_states[-1]
                if last_state.value is True:
                    return False
        return True

    # for this to work, tobor needs to do a better job of tracking locations
    # that's an extra step of sentence breakdowns in grammar_parser
    def apply(self, t):
        super().apply(t)

class GiveAction(Action):
    def __init__(self, name, e0, e1):
        super().__init__(name, e0, e1)

    def validate(self, reject_incomplete):
        super().validate(reject_incomplete)
        give_objs = self.get_action_targets()
        if isinstance(give_objs, dict):
            give_objs = give_objs["direct"]
        else:
            # reject_incomplete tells us if we should reject an incomplete action - True means return False
            return not reject_incomplete
        # the elements being given have to belong to a giver
        for give_obj in give_objs:
            valid_obj = True
            if any(give_obj.state_history["parent"]):
                valid_obj = False
                # due to how the states are constructed, it's possible for multiple elements to 'own' copies of a single element
                current_owners = give_obj.state_history["parent"][-1].value
                for owner in current_owners:
                    if owner in self.initiators:
                        valid_obj = True
            if not valid_obj:
                return False
        return True

    def apply(self, t):
        super().apply(t)
        receivers = self.get_action_targets()
        if isinstance(receivers, dict):
            give_objs = receivers["direct"]
            recipients = receivers["indirect"]
        else:
            print("Error: trying to give nothing!")
            return
        # there's some fun stuff we could do here re: duplication/sharing single instance of object
        # for now just assume everyone else gets a copy
        new_state = State("parent", recipients, t)
        for give_obj in give_objs:
            give_obj.state_history["parent"].append(new_state)

class EmplaceAction(Action):
    def __init__(self, name, e0, e1):
        super().__init__(name, e0, e1)

    def validate(self, reject_incomplete):
        # there are some interesting cases where an element couldn't emplace another
        # big case would be inanimate objects - but that's *very* hard to programmatically determine
        super().validate(reject_incomplete)
        receivers = self.get_action_targets()
        if isinstance(receivers, dict):
            receivers = receivers["direct"]
        for target in receivers:
            target_movement_states = [x for x in target.state_history["location"] if x.name == 'emplace']
            if any(target_movement_states):
                last_state = target_movement_states[-1]
                if last_state.value is True:
                    # it doesn't make sense to emplace an already fixed element
                    return False
        return True

    def apply(self, t):
        super().apply(t)
        receivers = self.get_action_targets()
        if isinstance(receivers, dict):
            receivers = receivers["direct"]
        # we can share the state between all receivers - it's functionally immutable
        new_state = State("emplace", True, t)
        for target in receivers:
            target.state_history["location"].append(new_state)

class TakeAction(Action):
    def __init__(self, name, e0, e1):
        super().__init__(name, e0, e1)

    def validate(self, reject_incomplete):
        super().validate(reject_incomplete)
        targets = self.get_action_targets()
        if isinstance(targets, dict):
            take_objs = targets["direct"]
            take_targets = targets["indirect"]
        else:
            return not reject_incomplete
        # the element being taken must belong to whomever it is taken from, if it belongs to anyone
        # note that, as with give, we don't mandate that the object already belong to the losers
        # this is to allow the transfer of 'common' items which a person could be assumed to have without specifying in the story
        # also note that groups of people can 'share' an object - consider gold being taken from a party of two
        # this could be expanded upon if we tracked element locations to enforce each localized group having the object, but alas
        for take_obj in take_objs:
            valid_obj = True
            if any(take_obj.state_history["parent"]):
                valid_obj = False
                # due to how the states are constructed, it's possible for multiple elements to 'own' copies of a single element
                current_owners = take_obj.state_history["parent"][-1].value
                for owner in current_owners:
                    if owner in take_targets:
                        valid_obj = True
            if not valid_obj:
                return False
        return True

    def apply(self, t):
        super().apply(t)
        targets = self.get_action_targets()
        if isinstance(targets, dict):
            take_objs = targets["direct"]
        else:
            print("Error: trying to take nothing!")
            return
        new_state = State("parent", self.initiators, t)
        for take_obj in take_objs:
            take_obj.state_history["parent"].append(new_state)

class DestroyAction(Action):
    def __init__(self, name, e0, e1):
        super().__init__(name, e0, e1)

    def validate(self, reject_incomplete):
        # we already check for redundant destruction in super method, and there's no concept of an indestructible element
        super().validate(reject_incomplete)


    def apply(self, t):
        super().apply(t)
        destroy_objs = self.get_action_targets()
        if isinstance(destroy_objs, dict):
            destroy_objs = destroy_objs["direct"]

        new_state = State('extant', False, t)
        for e in destroy_objs:
            e.state_history['extant'].append(new_state)

class FreeAction(Action):
    def __init__(self, name, e0, e1):
        super().__init__(name, e0, e1)

    def validate(self, reject_incomplete):
        super().validate(reject_incomplete)
        receivers = self.get_action_targets()
        if isinstance(receivers, dict):
            receivers = receivers["direct"]

        for target in receivers:
            target_movement_states = [x for x in target.state_history["location"] if x.name == 'emplace']
            last_state = target_movement_states[-1]
            if last_state.value is False:
                # it doesn't make sense to free an already freed element
                return False
        return True

    def apply(self, t):
        super().apply(t)

        receivers = self.get_action_targets()
        if isinstance(receivers, dict):
            receivers = receivers["direct"]

        new_state = State("emplace", False, t)
        for target in receivers:
            target.state_history["location"].append(new_state)