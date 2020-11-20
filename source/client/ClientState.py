import importlib
from common.Card import Card
from client.RunManagement import processRuns
from client.RunManagement import restoreRunAssignment
from client.RunManagement import wildsHiLo



class ClientState:
    """ This class store client state for access by different listeners

    It tracks things like 'interactivity', a player's hand, discard state, etc.
    It stores what is needed to compute scores and decide on move legality
    """

    def __init__(self, ruleset = None):
        """Initialize a state tracker for a given client"""
        if ruleset is not None:
            rule_module = "common." + ruleset
        else:
            #This is the unit test case - we may want to put a dummy ruleset in
            print("In unittest mode - using HandAndFoot rules")
            rule_module = "common.HandAndFoot"

        self.rules = importlib.import_module(rule_module)
        # Turn phase handled by controller
        self.turn_phase = 'inactive'  # hard coded start phase as 'not my turn'
        self.round = -1  # Start with the 'no current round value'
        self.name = "guest"
        # Will need to know player index in Liverpool because prepare cards buttons shared, but designated player
        # has to initiate play in that player's sets and runs.
        self.player_index = 0 # needed for Liverpool, will update when play cards.
        self.reset()  # Start with state cleared for a fresh round

    def getPlayerIndex(self, player_names):
        """This will udpate player index if another player drops out. """
        self.player_index = player_names.index(self.name)

    def dealtHands(self, hands):
        """Store the extra hands dealt to player for use after first hand is cleared"""
        self.newCards(hands[0])
        self.hand_list = hands[1:]
        
    def nextHand(self):
        """Transition to the next hand in the hand_list"""
        if len(self.hand_cards) > 0:
            raise Exception("You can't pick up your foot while you have cards left in your hand.")
        self.hand_cards = self.hand_list.pop()
        
    def checkGoneOut(self):
        """Check if a player has gone out"""
        if len(self.hand_cards) > 0:
            return False
        if len(self.hand_list) > 0:
            return False
        return self.rules.goneOut(self.played_cards)

    def scoreRound(self):
        """Get score for round"""
        # Need to combine hand an foot for cancellation with played cards
        unplayed_cards = self.hand_cards
        for hand in self.hand_list:
            unplayed_cards += hand
        score = self.rules.scoreRound(self.played_cards, unplayed_cards, self.went_out)
        return score

    def reset(self):
        """Clear out round specific state to prepare for next round to start"""
        self.hand_list = []
        self.hand_cards = []
        #   If self.rules.Shared_Board is False (HandAndFoot) this is dictionary of
        #   cards played by this client.
        #   If self.rules.Shared_Board is True (Liverpool)
        #   it is a dictionary containing cards played by all players, hence it is derived from
        #   data: visible cards, which is processed in method: visible_scards[{...}]

        self.played_cards = {}
        self.went_out = False
        self.discard_info = [None, 0]

    def newCards(self, card_list):
        """Update the cards in hand"""
        for card in card_list:
            self.hand_cards.append(card)

    def playCards(self, prepared_cards, visible_scards=[{}], player_index=0):
        """Move cards from hand to board if play follows rules, else inform what rule is broken."""

        # First check that all the cards are in your hand.
        self.player_index = player_index
        tempHand = [x for x in self.hand_cards]
        try:
            for card_group in prepared_cards.values():
                for card in card_group:
                    tempHand.remove(card)
        except ValueError:
            raise Exception("Attempted to play cards that are not in your hand")
        # Check ruleset to determine whether self.played_cards = all visible cards or cards that this client played.
        if not self.rules.Shared_Board:
            self.rules.canPlay(prepared_cards, self.played_cards, self.round)
            for key, card_group in prepared_cards.items():
                for card in card_group:
                    self.hand_cards.remove(card)
                    self.played_cards.setdefault(key, []).append(card)
        elif self.rules.Shared_Board:
            # Review Notes
            # todo: move these to documentation Review question -- should I keep them here, too?
            # Unlike in HandAndFoot, where self.played_cards was used to check rules,
            # in Liverpool and other shared board games need to consider all of the played cards.
            # Played cards (in deserialized form) are in visible_scards (in serialized form), which is obtained
            # from controller.
            # (Path taken by visible_scards:
            #          Tableview gets the serialized cards every cycle to keep display up to date,
            #          In handview.update tableview.visible_scards list is passed to handview.visible_scards
            #          No need to process this unless playing cards, in which case visible_scards passed
            #          to controller and then to clientState, where only list item is deserialized and put in
            #          dictionary self.played_cards
            numsets = self.rules.Meld_Threshold[self.round][0]
            # restoreRunAssignment converts all serialized cards to cards and processes self.played_cards
            # that are in runs so that positions of Wilds and Aces are maintained.
            # This could be made obsolete by adding tempnumbers to card serialization.
            self.played_cards = restoreRunAssignment(visible_scards[0], self.rules.wild_numbers, numsets)
            self.rules.canPlay(prepared_cards, self.played_cards, self.player_index, self.round)
            # play is legal, so rebuild played_cards with cards appropriately sorted and tempnumbers properly assigned.
            combined_cards = self.rules.combineCardDicts(self.played_cards, prepared_cards)
            self.played_cards = {}
            for k_group, card_group in combined_cards.items():
                # process runs from combined_cards (if k_group[1] > numsets, then it is a run).
                if k_group[1] >= numsets:
                    processed_group, wild_options, unassigned_wilds = processRuns(card_group, self.rules.wild_numbers)
                    print('in client state, line 136')
                    print(wild_options)
                    print(unassigned_wilds)
                    if len(unassigned_wilds) > 0:
                        textnote = "For the " + str(processed_group[0].suit) + " run: "
                        for card in processed_group:
                            textnote = textnote + str(card.number) + ','
                        textnote = textnote + "should the wild be high or low?  type H or L ?"
                        # todo: _state doesn't know about hand_view.
                        # hand_view.controller.note = textnote
                        print(textnote)
                        # todo: where should wildsHiLo go?? Do both capital and lower case L work, ....
                        # processed_group = HandManagement.wildsHiLo(processed_group, wild_options, unassigned_wilds)
                    # At this point all wilds should have been set properly.
                else:
                    #todo: need to sort sets?  get user feedback.
                    processed_group = card_group
                self.played_cards[k_group] = processed_group
            # unlike HandAndFoot, self.played_cards includes cards played by everyone.
            for key, card_group in prepared_cards.items():
                for card in card_group:
                    self.hand_cards.remove(card)


    def getValidKeys(self, card):
        """Get the keys that this card can be prepared with"""
        return self.rules.getKeyOptions(card)

    def pickupPileRuleCheck(self, prepared_cards):
        """Confirm a player can pick up the pile with the prepared cards"""
        # check there are enough cards
        if self.discard_info[1] < self.rules.Pickup_Size:
            text = 'Cannot pickup the pile until there are ' + str(self.rules.Pickup_Size) + ' cards.'
            raise Exception(text)
        return self.rules.canPickupPile(self.discard_info[0], prepared_cards, self.played_cards, self.round)

    def discardCards(self, card_list):
        """Discard cards from hand"""
        if len(card_list) != self.rules.Discard_Size:
            raise Exception("Wrong discard size. Must discard {0} cards".format(self.rules.Discard_Size))
        # check that all the cards are in your hand
        tempHand = [x for x in self.hand_cards]
        try:
            for card in card_list:
                tempHand.remove(card)
        except ValueError:
            raise Exception("Attempted to discard cards that are not in your hand")
        for card in card_list:
            self.hand_cards.remove(card)

    def updateDiscardInfo(self, top_card, size):
        """Update the discard information"""
        self.discard_info = [top_card, size]
    
    def getHandStatus(self):
        """Bundles public information in the format needed for sending to the server"""
        ### Public info has a hard coded order for interpretation - see the wiki to make sure it is kept consistent
        return [self.turn_phase, len(self.hand_cards), len(self.hand_list)]
