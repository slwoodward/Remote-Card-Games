from server.PlayerChannel import PlayerChannel
from server.ServerState import ServerState

from PodSixNet.Server import Server
from PodSixNet.Channel import Channel

from time import sleep          # only used in Liverpool draft.

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
        # todo: Shared_Board should probably be set in Ruleset.py, not here.
        # todo: but might not need it (jury still out).
        if ruleset == "Liverpool":
            self.Shared_Board = True
            self.visible_cards_now = {}
        else:
            self.Shared_Board = False
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
        self.turn_index = self.round    # define which player starts the next round.
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


    def nextTurn(self):
        """Advance to the next turn"""

        '''
        if self.Shared_Board:
            print('in GameServer.nexTurn method--- have bug with how its written below.')
            print('possible fix would be to use combineDict method to take union of groups in dicionaries....')
            print('will need to go through step to make certain that same card doesnt appear 2x in dictionary.')
            print('first make certain its not another bug causing played cards to be lost.')
            print('next player is not getting self.cards_on_board!!!')
            print(self.players[self.turn_index])
            # with a shared board every player sees the same board.
            #todo: remove debugging print statements
            print(self.turn_index)
            print('self.players[self.turn_index].visible_cards')
            print(self.players[self.turn_index].visible_cards)
            print(self.players[self.turn_index])
            self.cards_on_board = self.players[self.turn_index].visible_cards
            # above are debugging print statements
            #
            # used for games with Shared_Board=True, need to update visible cards immediately, before next turn begins.
            # todo: fix bug --
            # Observed with 2 players :
            # played cards are disappearing when discard button is hit.
            # they reappear the next time it is that player's turn.
            # Next 2 lines are effort to fix bug, but they didn't work.
            self.players[self.turn_index].visible_cards = self.cards_on_board # this probably is done.
            self.Send_broadcast({"action": "publicInfo", "player_names": [p.name for p in self.players], "visible_cards": [self.cards_on_board], "hand_status": [p.hand_status for p in self.players]})
            print('in GameServer, line 121, cards_on_board:')
            print( [self.cards_on_board])
            #
        '''
        # note for review: want to send visible_cards one more time before next player starts, so there
        # is time for the active players played_cards variable to be updated, and transmitted back to
        # server.
        # todo: double check that this doesn't wipe out the last players plays.

        '''
        if self.Shared_Board:
            visible_cards_now = v_cards[self.turn_index]
            sleep(1.0)
            # todo:  making sure that visible cards is updated before broadcast one more time before
            #  switching turns.  Find a better way.
            self.Send_broadcast({"action": "publicInfo", "player_names": [p.name for p in self.players],
                                 "visible_cards": [visible_cards_now],
                                 "hand_status": [p.hand_status for p in self.players]})
        '''
        newIndex = (self.turn_index + 1) % len(self.players)
        self.turn_index = newIndex
        self.players[self.turn_index].Send({"action": "startTurn"})
        '''if self.Shared_Board:
            sleep(1.0)
        '''
        # prevent out of date version of visible cards from being broadcast.
        #  Hopefully 1.0 sec is adequate time.
        # todo: Come up with a better way then simply waiting to make certain that visible_cards
        #  is accurately being updated.
        #  todo: Note that this should not be hardcoded here, move to a more obvious location.
        
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
        # On server keep them in serialized form.

        if self.Shared_Board:
            # Liverpool -- each player can play on any players cards.
            debuggingFlag = True
            if debuggingFlag:
                print('at line 173')
                print(self.players)
                self.v_cards = [p.visible_cards for p in self.players]
                if len(self.v_cards) == 0:
                    self.v_cards = [{}]
                print('at line 180')
                print(self.v_cards)
                # brainstorm -- set self.visible_cards_now to the element in v_cards with the most cards.
                max_len = -1
                self.visible_cards_now = {}
                print('at line 187 in gameserver')
                for v_cards_dict in self.v_cards:
                    print('line 188 in gameserver')
                    print(v_cards_dict)
                    temp_length = 0
                    for key, scard_group in v_cards_dict.items():
                        print(key)
                        print(scard_group)
                        print(len(scard_group))
                        temp_length = temp_length + len(scard_group)
                        print(temp_length)
                    if temp_length > max_len:
                        self.visible_cards_now = v_cards_dict
                        print('at line 190 in gameserver.py')
                        print(temp_length)
                        print(self.visible_cards_now)
                self.Send_broadcast({"action": "publicInfo", "player_names": [p.name for p in self.players],"visible_cards": [self.visible_cards_now],"hand_status": [p.hand_status for p in self.players]})

                '''
                earlier attempt --
                #todo: double check that this doesn't wipe out the last players plays.
                # There should be delay due to discard.
                # visible_cards_now = self.v_cards[self.turn_index]
                if len(self.v_cards) > 0:
                    visible_cards_now = self.v_cards[0]
                    self.Send_broadcast({"action": "publicInfo", "player_names": [p.name for p in self.players],"visible_cards": visible_cards_now,"hand_status": [p.hand_status for p in self.players]})
                '''
            else:
                self.Send_broadcast({"action": "publicInfo", "player_names": [p.name for p in self.players],"visible_cards": [p.visible_cards for p in self.players],"hand_status": [p.hand_status for p in self.players]})
        else:
            # HandAndFoot -- each player can only play on their own cards.
            # discovered that this HAS to be strung out long or it doesn't work properly.
            self.Send_broadcast({"action": "publicInfo", "player_names": [p.name for p in self.players], "visible_cards": [p.visible_cards for p in self.players], "hand_status": [p.hand_status for p in self.players]})


    def Send_discardInfo(self):
        """Send the update to the discard pile"""
        info = self.getDiscardInfo()
        self.Send_broadcast({"action": "discardInfo", "top_card": info[0].serialize(), "size": info[1]})

