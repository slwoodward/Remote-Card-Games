from server.PlayerChannel import PlayerChannel
from server.ServerState import ServerState

from PodSixNet.Server import Server
from PodSixNet.Channel import Channel

class GameServer(Server, ServerState):
    channelClass = PlayerChannel

    def __init__(self, localaddr, ruleset):
        """This overrides the library server init
        It's a place to do any 'on launch' actions for the server
        """
        Server.__init__(self, localaddr=localaddr)
        ServerState.__init__(self, ruleset)
        self.players = []
        self.in_round = False
        self.game_over = False
        #todo: Shared_Board should be set in Ruleset.py, not here.
        if ruleset == "Liverpool":
            self.cards_on_board = {}  # used for games with Shared_Board=True...
            self.Shared_Board = True
            print('Shared_Board is True')
        else:
            self.Shared_Board = False
            print('Shared_Board is False')

        print('Server launched')

    def Connected(self, channel, addr):
        """Called by podsixnet when a client connects and establishes a channel"""
        if self.in_round:
            print(channel, 'Client tried to connect during active round, try again between rounds')
            channel.Send({"action": "connectionDenied"})
        else:
            self.players.append(channel)
            self.Send_publicInfo()
            print(channel, "Client connected")
            if self.round >= 0:
                print(channel, 'a client joined between rounds')

    def disconnect(self, channel):
        """Called by a channel when it disconnects"""
        if channel not in self.players:
            #Disconnecting a channel that never fully joined the game, do nothing
            return
        #For players who did join the game need to handle removing them safely
        self.delPlayer(channel)
         
    def checkReady(self):
        """Confirm if all players are ready to move on to next round"""
        if self.in_round:
            return False
        player_states = [p.ready for p in self.players]
        if False not in player_states:
            self.nextRound()
            self.Send_broadcast({"action":"clearReady"}) #Reset in preparation for next round end

    def nextRound(self):
        """Start the next round of play"""
        self.round += 1
        self.in_round = True
        if self.round > self.rules.Number_Rounds-1: #Need to take one off Number_Rounds because we index from zero
            #Game is over
            print("GAME OVER - CHECK LAST SCORE REPORT FOR FINAL RESULT")
            self.game_over = True
        self.prepareRound(len(self.players))
        for player in self.players:
            player.Send_deal(self.dealHands(), self.round)
        self.Send_scores()              # need to retransmit all the scores in case a player has joined between rounds
        self.turn_index = self.round
        self.nextTurn()

    def delPlayer(self, player):
        """Safely remove a player from the turn order
        
        Checks for game over if no more players and quits server
        Moves turn forward if it was deleted players turn
        """
        player_index = self.players.index(player)
        self.players.remove(player)
        self.Send_publicInfo()
        #Check for no more players
        if len(self.players) == 0:
            self.game_over = True
            return
        #Check if it was deleted players turn and if so, make sure next player can start
        if self.turn_index == player_index and self.in_round:
            self.turn_index = self.turn_index % len(self.players) 
            self.players[self.turn_index].Send({"action": "startTurn"})
        # todo: verify that losing player[0] does not crash Liverpool (because len(visible_scards)=0)


    def nextTurn(self):
        """Advance to the next turn"""

        if self.Shared_Board:
            print('in nexTurn method-make certain board updated with play at end of turn.')
            print(' this might not be necessary...')
            print(self.players[self.turn_index])
            # with a shared board every player sees the same board.
            self.cards_on_board = self.players[self.turn_index].visible_scards
            # used for games with Shared_Board=True
            print(self.cards_on_board)
        newIndex = (self.turn_index + 1) % len(self.players)
        self.turn_index = newIndex
        self.players[self.turn_index].Send({"action": "startTurn"})
        
    def Send_broadcast(self, data):
        """Send data to every connected player"""
        [p.Send(data) for p in self.players]

    def Send_endRound(self, player_name):
        """Notifies players that player_name has gone out and the round is over"""
        self.Send_broadcast({"action": "endRound", "player": player_name})
        
    def Send_scores(self):
        """Send the scores to all players"""
        round_scores = [p.scoreForRound(self.round) for p in self.players]
        total_scores = [sum(p.scores) for p in self.players]
        if None not in round_scores:
            self.Send_broadcast({"action": "scores", "round_scores": round_scores, "total_scores": total_scores})

    def Send_publicInfo(self):
        """Send the update to the melded cards on the table"""

        #NOTE: visible_cards needs to be serialized form to be transmitted.
        # On server keep them in serialized form, and call variable visible_scards.

        if self.Shared_Board:
            # with a shared board every player plays on the entire board. visible_scards contains just 1 dictionary.
            # self.cards_on_board is the most recent update to p.visible_scards.
            print('in Send_publicInfo method')
            print(self.players[self.turn_index])
            self.cards_on_board = self.players[self.turn_index].visible_scards
            print(self.cards_on_board)
            # Liverpool has a shared board.  visible cards is a list of dictionaries with just 1 entry.
            # method nextTurn
            self.Send_broadcast({"action": "publicInfo", "player_names": [p.name for p in self.players], "visible_cards": [self.cards_on_board], "hand_status": [p.hand_status for p in self.players]})
        else:
            # HandAndFoot -- each player can only play on their own cards.
            self.Send_broadcast({"action": "publicInfo", "player_names": [p.name for p in self.players], "visible_cards": [p.visible_scards for p in self.players], "hand_status": [p.hand_status for p in self.players]})


    def Send_discardInfo(self):
        """Send the update to the discard pile"""
        info = self.getDiscardInfo()
        self.Send_broadcast({"action": "discardInfo", "top_card": info[0].serialize(), "size": info[1]})


