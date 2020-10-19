import pygame
import textwrap
from PodSixNet.Connection import connection, ConnectionListener
import client.UIConstants as UIC
from common.Card import Card
from common.Liverpool import Meld_Threshold as Meld_Threshold_LP
from common.HandAndFoot import Meld_Threshold as Meld_Threshold_HF
from common.Liverpool import wild_numbers as wild_numbers_LP
from common.HandAndFoot import wild_numbers as wild_numbers_HF


class TableView(ConnectionListener):
    """ This displays publicly available info on all the players.

    HandAndFoot specific version is in TableView_HF. This version ALSO supports Liverpool
    """

    def __init__(self, display, ruleset):
        self.display = display
        self.ruleset = ruleset
        self.player_names = []
        self.visible_cards = []
        self.hand_status = []
        self.compressed_info = {}
        self.playerByPlayer(0)
        self.results = {}
        self.this_player_index = -1   # code review note -- this variable needed for Liverpool.
        if ruleset == 'Liverpool':
            self.Meld_Threshold = Meld_Threshold_LP
            self.wild_numbers = wild_numbers_LP
        elif ruleset == 'HandAndFoot':
            self.Meld_Threshold = Meld_Threshold_HF
            self.wild_numbers = wild_numbers_HF
        else:
            print(ruleset + ' is not supported')

    def playerByPlayer(self, round_index):
        self.round_index = round_index
        # Loop through players and display visible cards associated with each players' melded groups.
        if self.ruleset == 'HandAndFoot':
            self.compressSets(self.visible_cards)
        elif self.ruleset == 'Liverpool':
            # print('Tableview, line 45')
            # print(self.visible_cards)
            # self.compressGroups(self.visible_cards, self.round_index)
            self.compressGroups(self.visible_cards)
        num_players = len(self.player_names)
        # currently set-up with one player per column. May need to change that for more players.
        if num_players > 1:
            players_sp_w = UIC.Disp_Width / num_players
        else:
            players_sp_w = UIC.Disp_Width
        players_sp_top = UIC.Disp_Height / 5
        players_sp_h = UIC.Disp_Height / 2
        color_index = 0
        bk_grd_rect = (0, players_sp_top, players_sp_w, players_sp_h)
        for idx in range(num_players):
            player_name = self.player_names[idx]
            if self.ruleset == 'HandAndFoot'or self.ruleset == 'Liverpool':
                # compressed_info is calculated in compressSets for HandAndFoot and compressGroups for Liverpool.
                melded_summary = self.compressed_info[player_name]
            # elif self.ruleset == 'Liverpool':
            #    melded_summary =  self.compressed_info[player_name]  # compressed_info is calculated in compressGroups
            pygame.draw.rect(self.display, UIC.table_grid_colors[color_index], bk_grd_rect, 0)
            if len(self.hand_status[idx]) > 1:
                turnphase = self.hand_status[idx][0]
                numcards = self.hand_status[idx][1]
                foot = self.hand_status[idx][2]
                player_text1 = player_name
                player_text2 = str(numcards) + ' cards'
                if self.ruleset == 'HandAndFoot':
                    if foot > 0:
                        player_text2 = player_text2 + ' (in hand)'
                    else:
                        player_text2 = player_text2 + ' (in foot)'
                if turnphase == 'inactive':
                    text_surface1, text_rect1 = self.textObjects(player_text1, UIC.Medium_Text, UIC.Black)
                    text_surface2, text_rect2 = self.textObjects(player_text2, UIC.Small_Text, UIC.Black)
                else:
                    #todo: underline surface1 below...
                    text_surface1, text_rect1 = self.textObjects(player_text1, UIC.Big_Text, UIC.Black)
                    text_surface2, text_rect2 = self.textObjects(player_text2, UIC.Small_Text, UIC.Black)
            else:
                player_text1 = player_name
                player_text2 = ' (should be joining soon)'
                text_surface1, text_rect1 = self.textObjects(player_text1, UIC.Medium_Text, UIC.Black)
                text_surface2, text_rect2 = self.textObjects(player_text2, UIC.Small_Text, UIC.Black)
            y_coord = 0.05 * UIC.Disp_Height
            text_rect1.center = ((bk_grd_rect[0] + 0.5 * players_sp_w), (bk_grd_rect[1] + y_coord))
            self.display.blit(text_surface1, text_rect1)
            y_coord = y_coord + UIC.Medium_Text_Feed
            text_rect2.center = ((bk_grd_rect[0] + 0.5 * players_sp_w), (bk_grd_rect[1] + y_coord))
            self.display.blit(text_surface2, text_rect2)
            screen_loc_info = (bk_grd_rect, y_coord)
            if self.ruleset == 'HandAndFoot':
                self.display_melded_summary_HF(screen_loc_info, melded_summary)
            elif self.ruleset == 'Liverpool':
                self.display_melded_summary_LP(screen_loc_info, melded_summary)
            # print scores, if no score yet, (e.g. just began or new player just joined) print '---'
            if self.results.get(player_name) is not None:
                player_total_points = str(self.results[player_name])
            else:
                player_total_points = '---'
            text_surface, text_rect = self.textObjects(player_total_points, UIC.Small_Text, UIC.Blue)
            text_rect.center = (bk_grd_rect[0] + 0.5 * players_sp_w,
                                bk_grd_rect[1] + y_coord + (UIC.Small_Text_Feed * 13))
            self.display.blit(text_surface, text_rect)
            # Move to next players rectangle and color:
            bk_grd_rect = (bk_grd_rect[0] + players_sp_w, bk_grd_rect[1], bk_grd_rect[2], bk_grd_rect[3])
            color_index = (color_index + 1) % len(UIC.table_grid_colors)

    def compressSets(self, v_cards):
        """ HandAndFoot specific: Don't have space to display every card. Summarize sets of cards here. """

        self.compressed_info = {}
        # print(v_cards)
        for idx in range(len(v_cards)):
            summary = {}
            key_player = self.player_names[idx]
            melded = dict(v_cards[idx])
            for key in melded:
                set = melded[key]
                length_set = len(set)
                if length_set > 0:
                    wild_count = 0
                    for s_card in set:
                        # Need to change below to: if s_card.number == 0 or s_card.number == 2:
                        if s_card[0] in self.wild_numbers:
                            wild_count = wild_count + 1
                    summary[key] = (length_set, (length_set - wild_count), wild_count)
            self.compressed_info[key_player] = summary

    def compressGroups(self, v_cards):
        """ Liverpool specific: Don't have space to display every card. Summarize groups of cards here. """

        #todo: debugging and documentation.
        # v_cards are cards in serialized form. < explains problem with isWild??
        # Notes -- should move to documentation in future.
        # OBSOLETE -- Prepared_cards have one key per button, and it is a tuple (player#, and set/run #)
        # v_cards have two separate keys - first is player #, 2nd is set/run #.
        #
        self.compressed_info = {}
        # print('Tableview, line 143')
        # print(v_cards)
        for idx in range(len(v_cards)):
            summary = {}
            key_player = self.player_names[idx]
            melded = dict(v_cards[idx])
            # print('in Tableview, line 145, melded for player idx:')
            # print(melded)
            for key_button in melded:
                text = ''
                i_kb = int(key_button[1])
                i_mt = int(self.Meld_Threshold[self.round_index][0])
                if i_kb < i_mt:
                    this_set = melded[key_button]
                    l_this_set = len(this_set)
                    if l_this_set > 0:
                        idx_c = 0
                        card_number = int(this_set[idx_c][0])
                        while card_number == 0 and idx_c < l_this_set:
                            idx_c = idx_c + 1
                            card_number = this_set[idx_c][0]
                        text = 'SET of ' + str(card_number) + "'s: "
                        for idx_c in range(l_this_set):
                            if not this_set[idx_c][0] == 0:
                                text = text + this_set[idx_c][1] + ','
                            else:
                                text = text + 'Joker' + ','
                else:
                    this_run = melded[key_button]
                    l_this_run = len(this_run)
                    if l_this_run > 0:
                        idx_c = 0
                        card_suit = this_run[idx_c][1]
                        while card_suit == 'None' and idx_c < l_this_run:
                            idx_c = idx_c + 1
                            card_suit = this_run[idx_c][1]
                        text = 'Run in ' + card_suit + ": "
                        for idx_c in range(l_this_run):
                            text = text + str(this_run[idx_c][0]) + ','
                    #todo: replace following line with something briefer.
                summary[i_kb] = text
            self.compressed_info[key_player] = summary

    def display_melded_summary_HF(self, screen_loc_info, melded_summary):
        # This section is for HandAndFoot, where key is index of player
        #
        bk_grd_rect = screen_loc_info[0]
        y_coord = screen_loc_info[1]
        players_sp_w = bk_grd_rect[2]
        for key in melded_summary:
            if melded_summary[key][0] > 0:
                detail_str = str(melded_summary[key][0])
                detail_str = detail_str + ': (' + str(melded_summary[key][1]) + ', ' + str(melded_summary[key][2]) + ')'
                if melded_summary[key][0] > 6:
                    detail_str = detail_str + '<<<'
                if melded_summary[key][2] == 0:
                    text_color = UIC.Red
                else:
                    text_color = UIC.Black
                ykey = y_coord + (UIC.Small_Text_Feed * (key - 3))
                if key == 1:
                    player_text = 'Aces ' + detail_str
                    ykey = y_coord + (UIC.Small_Text_Feed * 11)
                elif key == 11:
                    player_text = 'Jacks ' + detail_str
                elif key == 12:
                    player_text = 'Queens ' + detail_str
                elif key == 13:
                    player_text = 'Kings ' + detail_str
                else:
                    player_text = str(key) + "'s  " + detail_str
                text_surface, text_rect = self.textObjects(player_text, UIC.Small_Text, text_color)
                text_rect.center = ((bk_grd_rect[0] + 0.5 * players_sp_w), (bk_grd_rect[1] + ykey))
                self.display.blit(text_surface, text_rect)

    def display_melded_summary_LP(self, screen_loc_info, melded_summary):
        # This section is used by Liverpool.  Each player has a different melded_summary.

        bk_grd_rect = screen_loc_info[0]
        y_delta = UIC.Disp_Height / 8
        y_coord = screen_loc_info[1] + (y_delta * 0.8)
        players_sp_w = bk_grd_rect[2]
        for key in melded_summary:
            if len(melded_summary[key]) > 0:
                this_buttons_group = str(melded_summary[key])
                ykey = y_coord + (y_delta * key)
                text_surface, text_rect = self.textObjects(this_buttons_group, UIC.Small_Text, UIC.Black)
                text_rect.center = ((bk_grd_rect[0] + 0.5 * players_sp_w), (bk_grd_rect[1] + ykey))
                self.display.blit(text_surface, text_rect)

    def textObjects(self, text, font, color):
        text_surface = font.render(text, True, color)
        return text_surface, text_surface.get_rect()

    ''' superfluous?
    def thisPlayerIndex(self, name):
        return self.player_names.index(name)
    '''

    #######################################
    ### Network event/message callbacks ###
    #######################################

    def Network_publicInfo(self, data):

        '''
        example of data (json structure) with two players, 'hhh' and 'sss' : 
        {'action': 'publicInfo', 'player_names': ['hhh', 'sss'], 'visible_cards': [{}, {}],
           'hand_status': [['inactive', 12, 1], [True, 14, 1]]}
        where 'inactive' is an example of a play state (possible states: 'inactive', 'draw', 'forcedAction', 'play' '''
        self.player_names = data["player_names"]
        self.visible_cards = data["visible_cards"]
        self.hand_status = data["hand_status"]
        # todo: do I need next line?
        self.playerByPlayer(0)
    
    def Network_scores(self, data):
        """Notification from the server of the scores, in turn order"""

        round_scores = data["round_scores"]
        total_scores = data["total_scores"]
        self.results = {}
        self.results_cmdscreen = ''
        for idx in range(len(self.player_names)):
            self.results[self.player_names[idx]] = total_scores[idx]
            self.results_cmdscreen= self.results_cmdscreen + "  [" + \
                                    self.player_names[idx] + ": " + str(round_scores[idx]) + " " + \
                                    str(total_scores[idx]) +  "] \r \n "
            print("{0} scored {1} this round, and  has {2} total".format(
                self.player_names[idx], round_scores[idx], total_scores[idx]))
        print(self.results_cmdscreen)
