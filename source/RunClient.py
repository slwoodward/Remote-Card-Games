import sys
from time import sleep
from time import time
from PodSixNet.Connection import connection, ConnectionListener
from client.ClientState import ClientState
from client.Controller import Controller
from client.CreateDisplay import CreateDisplay
from client.TableView import TableView            # this should support both Liverpool and HandAndFoot
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
        note = "You should connect once you've entered your name. Otherwise it is possible you have the wrong server or port#..."
        gameboard.render(note)
        playername = gameControl.checkNames(tableView.player_names)
    if ruleset == 'Liverpool' or ruleset == 'HandAndFoot':
        while True:
            # Primary game loop.
            this_round = handView.round_index
            player_index = tableView.player_names.index(playername)
            gameboard.refresh()
            handView.nextEvent()
            connection.Pump()
            gameControl.Pump()
            tableView.Pump()
            tableView.playerByPlayer(this_round)
            if  clientState.rules.Shared_Board:
                visible_scards = tableView.visible_scards
                handView.update(player_index, len(tableView.player_names), visible_scards)
            else:
                handView.update()
            note = gameControl.note
            gameboard.render(note)
            '''
            # -- card buying sidebar -----------
            if clientState.rules.Buy_Option and clientState.rules.buying_phase:
                timelimit = time() + clientState.rules.purchase_time
                print(timelimit)
                while clientState.rules.buying_phase and time() < timelimit:
                    if clientState.turn_phase == 'draw':
                        note = 'Discard card is up for sale, this may take '+ str(clientState.rules.purchase_time)+\
                               ' seconds, click on draw once more to proceed....'
                    else:
                        note = 'Discard card is up for sale, do you want it? [Y/N]'
                        # need to put in correct actions here (send message to server).
                    print(note)
                    gameboard.render(note)
                    print(time())
                    sleep(clientState.rules.purchase_time/5) # scaled for while debugging with internal print statements...
            # -- end of card buying sidebar -----------
            '''
            sleep(0.001)
    else:
        print('that ruleset is not supported.')

if __name__ == "__main__":
    if len(sys.argv) != 1:
        print("This version gets host:port and ruleSet after starting.")
        print("Do not include any arguments on command line")
    else:
        RunClient()
else:
    print("RunServer should not be imported anywhere")