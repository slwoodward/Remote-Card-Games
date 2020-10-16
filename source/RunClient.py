import sys
from time import sleep
from PodSixNet.Connection import connection, ConnectionListener
from client.ClientState import ClientState
from client.Controller import Controller
from client.CreateDisplay import CreateDisplay
from client.TableView import TableView            # this should support both Liverpool and HandAndFoot
# from client.TableView_HF import TableView_HF      # this is for HandAndFoot
from client.HandView import HandView
# imports below added so that can generate executable using pyinstaller.
import common.HandAndFoot
import common.Liverpool
import common.Card
import client.Button
import client.ClickableImage
import client.UICardWrapper
import client.UIConstants


def RunClient():
    if getattr(sys, 'frozen', False):
        os.chdir(sys._MEIPASS)
    """This is the launch point for the client.
    
    It sets up the various classes and starts the game loop
    """
    hostinfo = str(input("Enter the host:port[localhost:12345] ") or "localhost:12345")
    host, port = hostinfo.split(":")
    print(host)
    print(port)
    ruleset = str(input("Enter the ruleset[Liverpool] ") or "Liverpool")
    print(ruleset)
    connection.DoConnect((host, int(port)))
    clientState = ClientState(ruleset)
    gameControl = Controller(clientState)
    playername = gameControl.getName()
    gameboard = CreateDisplay(playername)
    if ruleset == 'Liverpool' or ruleset == 'HandAndFoot':
        tableView = TableView(gameboard.display, ruleset)
    else:
        print('that ruleset is not supported')
    handView = HandView(gameControl, gameboard.display, ruleset)
    current_round = handView.round_index
    while(len(tableView.player_names) < 1) or (tableView.player_names.count('guest') > 0 ):
        # Note that if two people join with the same name almost simultaneously, then both might be renamed.
        gameboard.refresh()
        connection.Pump()
        gameControl.Pump()
        tableView.Pump()
        tableView.playerByPlayer(current_round)
        note = "adding your name to list of player names"
        gameboard.render(note)
        playername = gameControl.checkNames(tableView.player_names)
        # Liverpool needs every player name to be unique, and those names must be reflected accurately
        # in player_names from the beginning.
        # This is because buttons are keyed on tuple that includes player_name.
        # while - loop below continues until this player's name is in tableView.player_names.
        # Game won't begin until all users hit OK button, and the last player cannot do that until their
        # name is properly registered.
        # note for code review -- I checked using remove server, ruleset=HandAndFoot, and the name checking below works.
        safeguard = 1  # avoid an infinite loop.
        while playername not in tableView.player_names and safeguard < 1000:
            print(tableView.player_names)
            sleep(.01)
            gameboard.refresh()
            connection.Pump()
            gameControl.Pump()
            tableView.Pump()
            tableView.playerByPlayer(current_round)
            if safeguard % 100 == 1:
                note = note + ' .'
                gameboard.render(note)
            safeguard = safeguard + 1
        if safeguard > 999:
            print('problem with connection -- your name was not updated on server.')
    if ruleset == 'Liverpool' or ruleset == 'HandAndFoot':
        while True:
            # Primary game loop.
            this_round = handView.round_index
            # player_index = tableView.player_names.index(playername)
            gameboard.refresh()
            handView.nextEvent()
            connection.Pump()
            gameControl.Pump()
            tableView.Pump()
            tableView.playerByPlayer(this_round)
            # note for code review:
            # - for Liverpool need to put handView.update on TOP of playerByPlayer.
            # added tableView.player_names and visible_cards
            # because Liverpool needs info on other players (HandAndFoot did not).
            if ruleset == 'Liverpool':
                handView.update(playername, tableView.player_names, tableView.visible_cards)
            else:
                handView.update(playername, tableView.player_names)
            note = gameControl.note
            gameboard.render(note)
            sleep(0.001)
    elif ruleset =='':
        # note for code review:
        # Thought I would need different primary loops for 2 games, so put in if statement, then
        # realized I didn't need to do that YET.  The while loop below is from old version. Will delete
        # it once I'm confident that I won't want to revert.
        while True:
            # Primary game loop.
            this_round = handView.round_index
            player_index = tableView.this_player_index
            num_players = len(tableView.player_names)
            gameboard.refresh()
            handView.nextEvent()
            connection.Pump()
            gameControl.Pump()
            tableView.Pump()
            tableView.playerByPlayer(this_round) # for Liverpool need to put handView.update on TOP of playerByPlayer.
            handView.update(num_players, player_index)
            # added tableView.player_names because Liverpool needs # players (HandAndFoot did not).
            # tableView.playerByPlayer()
            note = gameControl.note
            gameboard.render(note)
            sleep(0.001)

if __name__ == "__main__":
    if len(sys.argv) != 1:
        print("This version gets host:port and ruleSet after starting.")
        print("Do not include any arguments on command line")
    else:
        RunClient()
else:
    print("RunServer should not be imported anywhere")