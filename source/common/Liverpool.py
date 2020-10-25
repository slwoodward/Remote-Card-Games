"""This is the ruleset reference for Liverpool

It defines:
- all the constants needed to set up and render the game for the server and client
- all the rule checking methods necessary for the client to play the game
"""
from common.Card import Card

import math

Game_Name = "Liverpool"

#todo: move Shared_Board from GamerServer.py to this file.
# currently in GamerServer.py Shared_Board = True for ruleset == Liverpool.
Draw_Size = 1
Pickup_Size = 1
Discard_Size = 1
play_pick_up = False # picking up the pile doesn't force cards to be played.
# isWild method not working in TableView so added wildnumbers. this statement
#todo: figure out issue with TableView.
wild_numbers = [0]

# Liverpool: number of sets and runs required to meld.
# first element below is temporary (for testing).
Meld_Threshold = [(1,1), (2,0), (1,1), (0,2), (3,0), (2,1), (1,2), (0,3)]
Number_Rounds = len(Meld_Threshold)  # For convenience

Deal_Size = 11
Hands_Per_Player = 1
notes = ["You can only pick up the pile at the start of your turn (buying not yet implemented)."]


def numDecks(numPlayers):
    """Specify how many decks of cards to put in the draw pile"""
    return math.ceil(numPlayers*0.6)


def singleDeck(n):
    """return a single deck of the correct type, n designates which deck of the numDecks to be used"""
    return Card.getJokerDeck(n)


def isWild(card):
    """returns true if a card is a wild"""
    if card.number in wild_numbers:
        return True
    else:
        return False


# todo: below is for checking on sets in HandAndFoot (not used for Liverpool sets)
#  for Liverpool runs will need this (though might be able to use something more sophisticated).
# player will probably have to state which set a card goes with, so this may be extraneous.
#  In Liverpool wild will need to be (NUMBER BETWEEN MIN-1 AND MAX+1) THAT HASN'T BEEN TAKEN.
def getKeyOptions(card):
    """returns the possible keys for the groups the card can go in"""
    if not isWild(card):
        return [card.number]
    else:
        return [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]


def canPlayGroup(key, card_group, this_round=0):
    """checks if a group can be played
    
    returns True if it can, otherwise raises an exception with an explanation.
    In Liverpool key of prepared (=assigned) cards = key of button = (name, button #)
    """
    print('in canPlayGroup, now checking sets and runs, but eased required length for faster testing.')
    if len(card_group) == 0:
        return True  # Need to allow empty groups to be "played" due to side-effects of how we combined dictionaries
    if key[1] < Meld_Threshold[this_round][0]:   # then this is a set.
        # check if this is a valid set.
        if len(card_group) < 1:
            raise Exception("Too few cards in set - minimum is 1 (will change to 3 later)")
        # check that group contains only wilds and one card_number.
        card_numbers = []
        num_cards = len(card_group)
        for card in card_group:
            if not isWild(card):
                card_numbers.append(card.number)
        num_naturals = len(card_numbers)
        unique_numbers = list(set(card_numbers))
        if len(unique_numbers) > 1:
            raise Exception("Cards in a set must all have the same rank (except wilds).")
        # check that have more naturals than wilds.
        unique_number = unique_numbers[0]
        if num_naturals <= (num_cards - num_naturals):
            text = "Too many wilds in set of " + str(unique_number) + "'s"
            raise Exception(text)
    else:
        # check that this is a valid run.
        if len(card_group) < 2:
            # todo:  for debugging only require  < 2, will need to change that to 4 later.
            raise Exception("Too few cards in run - minimum is 2 (for now) 4 (final version)")
        suits_in_run = []
        for card in card_group:
            if not isWild(card):
                suits_in_run.append(card.suit)
        unique_suits = list(set(suits_in_run))
        if len(unique_suits) > 1:
            raise Exception("Cards in a run must all have the same suit (except wilds).")
        print('-- run -----')

    print('-------')
    return True

def processRuns(card_group):
        # handle sorting of run, including placement of jokers.
        for card in card_group:
            print(card)
        card_group.sort(key=lambda wc: wc.tempnumber)
        print('--sorted-----')
        first_card = True
        groups_jokers = []
        temp_run_group = []
        for card in card_group:
            print(temp_run_group)
            print(card)
            if card.tempnumber == 0:
                print('there is an unassigned joker in this group, will try to automatically assign it')
                groups_jokers.append(card)
                for joker in groups_jokers:
                    print(joker)
            elif first_card:
                first_card = False
                temp_run_group.append(card)
            else:
                if card.tempnumber == (temp_run_group[-1].tempnumber + 1):
                    temp_run_group.append(card)
                elif card.tempnumber == (temp_run_group[-1].tempnumber + 2) and len(groups_jokers) > 1:
                    this_joker = groups_jokers[0]
                    groups_jokers.remove(this_joker)
                    this_joker.tempnumber = temp_run_group[-1].tempnumber + 1
                    temp_run_group.append(this_joker)
                    temp_run_group.append(card)
                else:
                    raise Exception('too big a gap between numbers')
        print('at line 139, next is groups_jokers, then temp_run_group')
        print(groups_jokers)
        print(temp_run_group)
        if len(groups_jokers) > 0:
            for this_joker in groups_jokers:
                this_joker.tempnumber = temp_run_group[-1].tempnumber + 1
                temp_run_group.append[joker]
                # todo: handle jokers properly -- this does not.
        card_group = temp_run_group
        return card_group

def canMeld(prepared_cards, round_index, player_index):
    """Determines if a set of card groups is a legal meld, called from canPlay."""
    #
    # This section differs from HandAndFoot.
    # debugging - still need to debug canMeld routine, but want to get past it for now....
    required_groups =  Meld_Threshold[round_index][0] + Meld_Threshold[round_index][1]
    valid_groups = 0
    for key, card_group in prepared_cards.items():
        if canPlayGroup(key, card_group, round_index) and key[0] == player_index:
            valid_groups = valid_groups + 1
    if required_groups > valid_groups :
        raise Exception("Must have all the required sets and runs to meld")
    return True

def canPickupPile(top_card, prepared_cards, played_cards, round_index):
    """Determines if the player can pick up the pile with their suggested play-always True for Liverpool"""
    return True

def canPlay(prepared_cards, visible_cards, player_index, round_index):
    """Confirms if playing the selected cards is legal"""

    # what groups have already been played?
    played_groups = []
    for key, cards in visible_cards[0].items():
        if len(cards) > 0:
            played_groups.append(key)
    print('line 154 in Liverpool.py, canPlay method - played_groups:')
    print(played_groups)
    # does player attempt to play on another player's groups before that player has melded ?
    for key, cards in prepared_cards.items():
        if len(cards) > 0:
            group_key = key
            if not group_key[0] == player_index and group_key not in played_groups:
                raise Exception("You are not allowed to begin another player's sets or runs.")
    # Has player already melded? -- if so visible_cards[player_index] will NOT be empty.
    if (player_index,0) not in played_groups:
        # if a player has already melded than key = (player_index,0) will have dictionary entry with cards.
        return canMeld(prepared_cards, round_index, player_index)
    # gathering all played and prepared_cards into single dictionary (needed for rule checking).
    # For Runs:
    #     for visible_cards, must first check if either an Ace is high or if a Joker is on either end of the run,
    #     before combining dictionaries, so that the values do not change (unless a joker is replaced).
    #     if so, then set their card.tempnumber so that they will be in correct position when sorting.
    for k_group, card_group in visible_cards[0].items():       # pre-process visible_cards
        if k_group[1] >= Meld_Threshold[round_index][0]:       # then this is a run.
            if card_group[-1].number == 1:            # reset tempnumber for Aces/jokers if they are at the end
                card_group[-1].tempnumber = 14
            elif card_group[-1].number == 0:
                card_group[-1].tempnumber = card_group[-2].tempnumber + 1
                print('last card in visible cards run is a joker. tempnumber is' )
                print(card_group[-1].tempnumber)
            if card_group[0].number ==0 :            # reset tempnumber for jokers if they are at the beginning.
                card_group[0].tempnumber = card_group[1].tempnumber - 1
    combined_cards = combineCardDicts(visible_cards[0], prepared_cards)
    #  -- debug print statements below
    print('visible cards should be sorted, prepared cards appended to the end:')
    for k_group, card_group in combined_cards.items():
        print('--just prior to calling processRuns---')
        for eachcard in card_group:
            print(eachcard)
    # -- debug print statements above--
    for k_group, card_group in combined_cards.items():
        if k_group[1] >= Meld_Threshold[round_index][0]:
            processed_group = processRuns(card_group)               # process runs from combined_cards
            canPlayGroup(k_group, processed_group, round_index)
            card_group = processed_group
        print('--just after calling processRuns---')
        for eachcard in card_group:
            print(eachcard)
    return True

def combineCardDicts(dict1, dict2):
    """Combine two dictionaries of cards, such as played and to be played cards.

    This should work for both cards and serialized cards."""
    combined_cards = {}
    for key in set(dict1).union(dict2):
        combo_list = []
        for card in dict1.setdefault(key, []):
            combo_list.append(card)
        for card in dict2.setdefault(key, []):
            combo_list.append(card)
        combined_cards[key] = combo_list
    return combined_cards


def cardValue(card):
    """Returns the point value for a card"""
    if card.number in [2, 3, 4, 5, 6, 7, 8, 9]:
        return 5
    if card.number in [10, 11, 12, 13]:
        return 10
    if card.number == 1:
        return 15
    if card.number == 0:
        return 20
    raise ValueError("Card submitted is not a legal playing card option")


def goneOut(played_cards):
    """Returns true if the played set of cards meets the requirements to go out

    This DOES NOT confirm that a player has no cards, that is the controllers job
    For Liverpool if the player has no cards, then they've gone out.
    Need to let server know, but no additional requirements.
    Might not even need this function...
    """
    return True


def scoreGroup(card_group):
    """Scores a group of cards for raw value"""
    score = 0
    for card in card_group:
        score += cardValue(card)
    return score


def scoreRound(irrelevant1, unplayed_cards, irrelevant2):
    """Calculates the score for a player for a round"""
    score = scoreGroup(unplayed_cards)
    return score
