import random                  # will be used to assign unique names
from time import sleep
from common.Card import Card
from PodSixNet.Connection import connection, ConnectionListener

Turn_Phases = ['inactive', 'draw', 'forcedAction', 'play']
Forbidden_Names = ['guest','']

class Controller(ConnectionListener):
    """ This client connects to a GameServer which will host a cardgame

    The client displays the game _state it receives from the server
    It validates and submits player actions to the server during the player's turn
    It submits its score on round or game end
    """

    def __init__(self, clientState):
        self._state = clientState
        self.prepared_cards = {}     #This is the dict of cards prepared to be played
        self.setName()
        self.ready = False
        self.note = "Game is beginning."
        # variables needed for games with Shared_Board == True (i.e. Liverpool):
        self.Meld_Threshold = self._state.rules.Meld_Threshold
        self.player_index = 0
        self.visible_scards = [{}] # if Shared_Board both HandView and TableView use data:visible cards.
        # variables needed if Buy_Option is True
        self.buying_opportunity = False

    ### Player Actions ###
    def setName(self):
        """Set up a display name and send it to the server"""

        # to prevent duplicate names, displayname = 'guest' is forbidden.
        # Forbidden names are defined at the beginning of this controller.
        # May as well allow other names to be forbidden, too (for fun :) )
        # if name is in list of forbidden names, then changeName is called.
        displayName = input("Enter a display name: ")
        if displayName in Forbidden_Names:
            self.note = "Sorry, but that name ('"+displayName+"') is forbidden."
            self._state.name = self.changeName()
        else:
            self._state.name = displayName
            connection.Send({"action": "displayName", "name": displayName})

    def checkNames(self, player_names):
        # Check that no names are duplicated.
        moniker = self._state.name
        if player_names.count(moniker) > 1 :
            self.note = self._state.name + ' is already taken.'
            moniker = self.changeName()
        return moniker

    def changeName(self):
        # Check that no names are duplicated.
        name2 = "Bob" + str(random.randint(101, 999))
        self.note =self.note + ' ' + self._state.name + ' you shall now be named: ' + name2
        # it is possible (though unlikely) that two players might still end up with the
        # same name due to timing, (or 1/898 chance that the same Bob name is chosen)
        # but we do not deal with these corner cases.
        self._state.name = name2
        connection.Send({"action": "displayName", "name": name2})
        return name2

    def setReady(self, readyState):
        """Update the player's ready state with the server"""
        self.ready = readyState
        connection.Send({"action": "ready", "state": self.ready})

    def discard(self, discard_list):
        """Send discard to server"""
        if self._state.turn_phase != Turn_Phases[3]:
            self.note = "You can only discard at the end of your turn (after having drawn)."
            return False
        try:
            self._state.discardCards(discard_list)
            self.handleEmptyHand(True)
            connection.Send({"action": "discard", "cards": [c.serialize() for c in discard_list]})
            self._state.turn_phase = Turn_Phases[0] #end turn after discard
            self.note = "Discard completed. Your turn is over."
            self.sendPublicInfo()
            return True
        except Exception as err:
            self.note = "{0}".format(err)
        return False

    def draw(self):
        """Request a draw from the server"""
        if self._state.turn_phase != Turn_Phases[1]:
            self.note = "You can only draw at the start of your turn"
            return
        connection.Send({"action": "draw"})
        #Transition phase immediately to avoid double draw
        self._state.turn_phase = Turn_Phases[3]

    def drawWithBuyOption(self):
        """ in cards with buy option use this method instead of draw (above)"""
        if self._state.turn_phase != Turn_Phases[1]:
            self.note = "You can only draw at the start of your turn"
            return
        connection.Send({"action": "drawWithBuyOption"})
        # Transition phase immediately to avoid double draw
        self._state.turn_phase = Turn_Phases[3]

    def wantTopCard(self, want_card):
        if want_card:
            print('player signaled wants top card')
        else:
            print('player does not want to buy top card')
        self.buying_opportunity = False # can't change your mind.
        self.sendBuyResponse(want_card)  # this is where send response to network, player channel.

    def pickUpPile(self, note):
        """Attempt to pick up the pile"""
        if self._state.turn_phase != Turn_Phases[1]:
            self.note = note
            return
        try:
            self._state.pickupPileRuleCheck(self.prepared_cards)
        except Exception as err:
            self.note = "{0}".format(err)
        else:
            if self._state.rules.play_pick_up:
                self._state.turn_phase = Turn_Phases[2] #Set turn phase to reflect forced action
                self.note = "Waiting for new cards to make required play."
            else:
                self._state.turn_phase = Turn_Phases[3] # No action required if rules.play_pick_up = False
            connection.Send({"action": "pickUpPile"})

    def makeForcedPlay(self, top_card):
        """Complete the required play for picking up the pile, (used in HandAndFoot but not Liverpool)"""
        self.note = "Performing the play required to pick up the pile."
        #Get key for top_card (we know it can be auto-keyed), and then prepare it
        key = self._state.getValidKeys(top_card)[0]
        self.prepared_cards.setdefault(key, []).append(top_card)
        #Can't just call prepared card b/c of turn phase checking
        #Set turn phase to allow play and then immediately make play
        self._state.turn_phase = Turn_Phases[3]
        self.play()

    def automaticallyPrepareCards(self, selected_cards):
        """HandAndFoot specific: Prepare selected cards to be played.
        
        Assumes all groups are sets.
        Fully prepares natural cards
        Returns options for where to play wild cards
        Returns message that you can't play 3s
        """
        if self._state.turn_phase == Turn_Phases[2]:
            self.note = "You can't change prepared cards while waiting to finish picking up the pile"
            return
        user_input_cards = []
        for wrappedcard in selected_cards:
            card = wrappedcard.card
            key_opts = []
            try:
                key_opts = self._state.getValidKeys(card)
            except Exception as err:
                #This note will probably be overwritten before the user sees it, unless they try to prepare only 3s
                self.note = "Did not prepare card: {0}".format(err) 
            else:
                if len(key_opts) == 1:
                    self.prepareCard(key_opts[0], card) #Automatically prepare as much as possible
                else:
                    user_input_cards.append([card, key_opts])
        return user_input_cards

    def assignCardsToGroup(self, assigned_key, selected_cards):
        """Assign cards to specific groups based on button clicked.

         Wilds are assigned to group, but if value ambiguous it is not determined until group is played.
         This method is needed in games where player explicitly assigns cards to groups (such as Liverpool).
         In games that are purely set-based (such as Hand and Foot) this is not used.
        """
        for wrappedcard in selected_cards:
            card = wrappedcard.card
            self.prepareCard(assigned_key, card)
        return

    def prepareCard(self, key, card):
        """Prepare the selected card with the specified key"""
        if self._state.turn_phase == Turn_Phases[2]:
            self.note = "You can't change prepared cards while waiting to finish picking up the pile"
            return
        self.prepared_cards.setdefault(key, []).append(card)

    def clearPreparedCards(self):
        """Clears prepared cards"""
        if self._state.turn_phase == Turn_Phases[2]:
            self.note = "You can't change prepared cards while waiting to finish picking up the pile"
            return
        self.prepared_cards = {}
        self.note = "You have no cards prepared to play"

    def play(self, player_index=0, visible_scards=[{}]):
        """Send the server the current set of played cards"""
        # player_index and visible_scards needed for rules checking in games with Shared_Board.
        #
        if self._state.turn_phase != Turn_Phases[3]:
            self.note = "You can only play on your turn after you draw"
            return
        try:
            self._state.playCards(self.prepared_cards, visible_scards, player_index)
            self.clearPreparedCards()
            self.handleEmptyHand(False)
            self.sendPublicInfo()
        except Exception as err:
            self.note = "{0}".format(err)
            return

    def handleEmptyHand(self, isDiscard):
        """Checks for and handles empty hand. 
        
        If they are out of their hand, transitions to the next hand.
        If they are out of all their hands checks if they are actually out
        If they are out notifies the server
        """
        if len(self._state.hand_cards) > 0:
            return False
        elif len(self._state.hand_list) > 0:
            self._state.nextHand()
            return False
        elif self._state.checkGoneOut():
            self.note = "You went out to end the round!"
            connection.Send({"action": "goOut"})
            self._state.went_out = True
            self._state.turn_phase = Turn_Phases[0] # end active state after going out.
            self.sendPublicInfo()
            return True
        else:
            self.note = "You have no cards left but aren't out, you have gone zaphod."
            if not isDiscard:
                #If you played to zaphod we need to let the server know your turn is over
                self._state.turn_phase = Turn_Phases[0]
                connection.Send({"action": "discard", "cards": []})
            return False

    '''def start_auction(self):
        """ For games with a buying option, tell server to broadcast buying opportunity."""
        connection.Send({"action": "start_auction"})
    '''

    ### Fetchers for handView ###
    def getName(self):
        """return player name for labeling"""
        return self._state.name
    
    def isReady(self):
        """return if the player is currently ready to move on"""
        return self.ready

    def getHand(self):
        """sends _state to UI"""
        return self._state.hand_cards.copy()

    def getPreparedCards(self):
        """lets the UI fetch prepared cards"""
        prepared_list = []
        for card_group in self.prepared_cards.values():
            prepared_list.extend(card_group)
        return prepared_list

    def getTurnPhase(self):
        """return if the player should be active"""
        return self._state.turn_phase

    def getDiscardInfo(self):
        """let the UI know the discard information"""
        return self._state.discard_info.copy()
    
    def sendPublicInfo(self):
        """Utility method to send public information to the server"""
        serialized_cards = {key:[card.serialize() for card in card_group] for (key, card_group) in self._state.played_cards.items()}
        status_info = self._state.getHandStatus()
        connection.Send({"action": "publicInfo", "visible_cards":serialized_cards, "hand_status":status_info})

    def sendBuyResponse(self, want_card):
        """ In games with opportunity to buy discards, this sends response to buying opportunities to server.  """
        connection.Send({"action": "buyResponse", "want_card": want_card})

    def lateJoinScores(self, score):
        """ When a player joins late the early rounds need to be assigned a score.  This does it. """
        connection.Send({"action": "reportScore", "score": score})

    #######################################
    ### Network event/message callbacks ###
    #######################################
    
    ### built in stuff ###
    def Network_connected(self, data):
        print("Connected to the server")
        self.note = "Connected to the server!"
    
    def Network_error(self, data):
        print('error:', data['error'])
        connection.Close()
    
    def Network_disconnected(self, data):
        print('Server disconnected')
        self.note = "Disconnected from the server :("
        exit()

    ### Setup messages ###
    def Network_connectionDenied(self, data):
        """Server denied the connection, likely due to a game already in progress"""
        print('Server denied connection request')
        self.note = "Server denied connection request :("
        connection.Close()

    ### Gameplay messages ###
    def Network_startTurn(self, data):
        if self._state.round == -1:
            #Ignore turns when between rounds
            return
        self._state.turn_phase = Turn_Phases[1]
        self.note = "Your turn has started. You may draw or attempt to pick up the pile"
        self.sendPublicInfo() #Let everyone know its your turn.

    def Network_buyingOpportunity(self, data):
        self.buying_opportunity = True
        #  Ignore this when between rounds or when there are no cards in discard pile.
        #todo: remove 2 lines below because almost certainly unnecessary.
        #  if self._state.round == -1 or self._state.discard_info[1] == 0:
        #     return
        self.note = "The {0} is for sale, Do you want to buy it? [y/n]".format(Card.deserialize(data["top_card"]))

    def Network_newCards(self, data):
        card_list = [Card.deserialize(c) for c in data["cards"]]
        self._state.newCards(card_list)
        if self._state.turn_phase == Turn_Phases[2]:
            #This is the result of a pickup and we have a forced action
            self.makeForcedPlay(card_list[0])
        # review note -- in Liverpool the note below
        # overwrites message on who bought card, AND was appearing on board of the person who bought card.
        if not self._state.rules.BuyOption:
            self.note = "You can now play cards or discard"
        self.sendPublicInfo() #More cards in hand now, need to update public information
    
    def Network_deal(self, data):
        self._state.round = data["round"]
        self._state.reset()
        hand_list = [[Card.deserialize(c) for c in hand] for hand in data["hands"]]
        #TODO: in HandAndFoot we want to allow the player to choose the order of the hands eventually
        self._state.dealtHands(hand_list)
        self.sendPublicInfo() #More cards in hand now, need to update public information

    def Network_discardInfo(self, data):
        top_card = Card.deserialize(data["top_card"])
        size = data["size"]
        self._state.updateDiscardInfo(top_card, size)
    
    def Network_endRound(self, data):
        """Notification that specified player has gone out to end the round"""
        out_player = data["player"]
        self.note = "{0} has gone out to end the round!".format(out_player)
        self._state.round = -1
        score = self._state.scoreRound()
        connection.Send({"action": "reportScore", "score": score})
        self.setReady(False)

    def Network_clearReady(self, data):
        self.setReady(False)

    def Network_buyingResult(self, data):
        buyer = data["buyer"]
        purchase = Card.deserialize(data["top_card"])
        self.note = "{0} has purchased {1}".format(buyer, purchase)

