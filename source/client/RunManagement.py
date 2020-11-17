from common.Card import Card

"""This file contains methods used in processing runs for Liverpool.

Some oddities -- it assumes that Aces can be Hi or Low but not both.

In order to preserve backwards compatibility with June 2020 distribution, it assumes that card.tempnumber is
not passed back and forth between the client and server. This only causes ambiguity in wilds and 
Aces at the ends of runs.   Method restoreRunAssignment takes care of this by assigning
wilds and Aces on ends of runs the appropriate tempnumber before processRuns is called.

To preserve info on whether Ace is assigned hi or low, if Ace is assigned low, then tempnumber is set to -1.
"""

def processRuns(card_group):
    """ handle sorting of run, including placement of wilds.  Handles minor rule checking.

    # processRuns does not presume length requirement or that all cards are in same suit.
    # it DOES presume that if Aces are not wild, then they are hi or low, but not both.
    """
    card_group.sort(key=lambda wc: wc.tempnumber)
    first_card = True
    groups_wilds = []
    temp_run_group = []
    aces_list =[]
    for card in card_group:                    # separate unassigned wilds and Aces from rest of run.
        if card.tempnumber in wild_numbers:
            groups_wilds.append(card)         # pull out wilds before Aces, in case Aces are wild.
        elif card.tempnumber == 1:
            aces_list.append(card)
        else:
            temp_run_group.append(card)
    card_group  = []                         # rebuild card_group below
    for card in temp_run_group:
        if first_card:
            first_card = False
            card_group.append(card)
        else:
            if card.tempnumber == (card_group[-1].tempnumber + 1):
                card_group.append(card)
            elif card.tempnumber == (card_group[-1].tempnumber + 2) and len(groups_wilds) > 0:
                this_wild = groups_wilds.pop(0)
                this_wild.tempnumber = card_group[-1].tempnumber + 1
                card_group.append(this_wild)
                card_group.append(card)
            elif card.tempnumber == card_group[-1].tempnumber:
                if isWild(card):
                    card.tempnumber = card.number
                    groups_wilds.append(card)
                elif isWild(card_group[-1]):
                    this_wild = card_group.pop(-1)
                    this_wild.tempnumber = this_wild.number
                    groups_wilds.append(card)
                else:
                    raise Exception('Card value already in the run.')
            else:
                raise Exception('too big a gap between numbers')
    #  Review note - Handle Aces after other cards, else ran into problem when wanted Ace, Joker, 3...
    # Rare for Ace Hi and Ace low to both be options. If they are, does it make a difference which one they are?
    # If run is A,2,Wild,4...J,Q,K,Wild then it does.
    if len(aces_list) > 0:
        if card_group[-1].tempnumber == 13 and not card_group[0].tempnumber == 2:
            this_ace = aces_list.pop(0)
            this_ace.tempnumber = 14
            card_group.append(this_ace)
        elif not card_group[-1].tempnumber == 13 and card_group[0].tempnumber == 2:
            this_ace = aces_list.pop(0)
            this_ace.tempnumber = -1
            card_group.insert(0, this_ace)
        elif card_group[-1].tempnumber == 13 and card_group[0].tempnumber == 2:
            print("IF ACE CAN BE HIGH OR LOW THAN AUTOMATICALLY MAKING IT LOW, RATHER THAN HANDLING CORNER CASE.")
            this_ace = aces_list.pop(0)
            this_ace.tempnumber = -1
            card_group.insert(0, this_ace)
    # possible to assign remaining Aces after wilds are assigned.
    while len(groups_wilds) > 0 :
        # todo: handle jokers properly -- ask if high or low when both are an option.
        this_wild = groups_wilds.pop(0)
        if card_group[-1].tempnumber < 14 and not isWild(card_group[-1]):
            this_wild.tempnumber = card_group[-1].tempnumber + 1
            card_group.append(this_wild)
        elif card_group[0].tempnumber > 1 and not isWild(card_group[0]):
            this_wild.tempnumber = card_group[0].tempnumber - 1
            card_group.insert(0, this_wild)
        else:
            raise Exception('you have too many jokers in a single Run')
    last_card_wild = False
    second2last_card_wild = False
    # todo: check to see if can play any remaining aces after wilds are placed.
    # todo: Need to get input from user, so move this method and restoreRunAssignments to controller.
    if len(aces_list) > 0:
        raise Exception('Cannot play Ace in designated run')
    for card in card_group:
        if (isWild(card) and last_card_wild) or (isWild(card) and second2last_card_wild):
            raise Exception('Must have two natural cards between wild cards in runs')
        second2last_card_wild = last_card_wild
        last_card_wild = isWild(card)
    return card_group

def restoreRunAssignment(visible_scards_dictionary, round_index):
    """ assign values to Wild cards and Aces in runs from server.

    Needed to maintain integrity of Wilds' assigned values in runs.  Server does not know tempnumbers
    (for backwards compatability not changing json between server and client).
    There's no ambiguity except for wilds and Aces at the ends of the run (processRuns handles wilds in middle).
    """

    if len(visible_scards_dictionary) == 0:
        return(visible_scards_dictionary)
    cardgroup_dictionary = {}
    for key, scard_group in visible_scards_dictionary.items():
        card_group = []
        for scard in scard_group:
            card = Card(scard[0], scard[1], scard[2])
            card_group.append(card)
        cardgroup_dictionary[key] = card_group
    for k_group, card_group in cardgroup_dictionary.items():
        if k_group[1] >= Meld_Threshold[round_index][0] and len(card_group) > 1:       # check if this is a run.
            if card_group[-1].number in wild_numbers:    # reset tempnumber for Wilds/Aces if they are at the end.
                card_group[-1].assignWild(card_group[-2].tempnumber + 1)
            elif card_group[-1].number == 1:
                card_group[-1].assignWild(14)
            if card_group[0].number in wild_numbers:    # reset tempnumber for wild cards if they are at the beginning.
                card_group[0].assignWild(card_group[1].tempnumber - 1)
            # todo: be sure to preserve this in documentation.  If Ace is assigned low, then tempnumber is -1.
            elif card_group[0].number == 1:
                card_group[0].tempnumber = -1
        return cardgroup_dictionary
