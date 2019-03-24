class Card():
    """ This defines a playing card for use in the game

    Every card is an integer number and a suit (jokers have suit None and number 0)
    A card can tell you its color for rule checking
    """
    def __init__(self, number, suit):
        self._number = number
        if suit not in [None, 'Spades', 'Hearts', 'Diamonds', 'Clubs']:
            raise Exception("Invalid Suit")
        self._suit = suit

    def GetColor(self):
        if self._suit in ['Spades', 'Clubs']:
            return 'Black'
        if self._suit in ['Hearts', 'Diamonds']:
            return 'Red'
        return None #For jokers

    def Serialize(self):
        """translate into a format podsixnet can translate"""
        return (self._number, self._suit)

    def Deserialize(representation):
        """create a card object from the podsixnet transportable serialization"""
        return Card(representation[0], representation[1])

    def __str__(self):
        if self._suit is None:
            return "Joker"
        if self._number > 10:
            if self._number == 11:
                return "Jack of " + self._suit
            if self._number == 12:
                return "Queen of " + self._suit
            if self._number == 13:
                return "King of " + self._suit
        if self._number == 1:
            return "Ace of " + self._suit
        return "{0} of {1}".format(self._number, self._suit)

    def __repr__(self):
        return "({0}, {1})".format(self._number, self._suit)

    def GetStandardDeck():
        """Provides a standard 52 card deck"""
        return [Card(1, 'Spades'),
                Card(2, 'Spades'),
                Card(3, 'Spades'),
                Card(4, 'Spades'),
                Card(5, 'Spades'),
                Card(6, 'Spades'),
                Card(7, 'Spades'),
                Card(8, 'Spades'),
                Card(9, 'Spades'),
                Card(10, 'Spades'),
                Card(11, 'Spades'),
                Card(12, 'Spades'),
                Card(13, 'Spades'),
                Card(1, 'Hearts'),
                Card(2, 'Hearts'),
                Card(3, 'Hearts'),
                Card(4, 'Hearts'),
                Card(5, 'Hearts'),
                Card(6, 'Hearts'),
                Card(7, 'Hearts'),
                Card(8, 'Hearts'),
                Card(9, 'Hearts'),
                Card(10, 'Hearts'),
                Card(11, 'Hearts'),
                Card(12, 'Hearts'),
                Card(13, 'Hearts'),
                Card(1, 'Diamonds'),
                Card(2, 'Diamonds'),
                Card(3, 'Diamonds'),
                Card(4, 'Diamonds'),
                Card(5, 'Diamonds'),
                Card(6, 'Diamonds'),
                Card(7, 'Diamonds'),
                Card(8, 'Diamonds'),
                Card(9, 'Diamonds'),
                Card(10, 'Diamonds'),
                Card(11, 'Diamonds'),
                Card(12, 'Diamonds'),
                Card(13, 'Diamonds'),
                Card(1, 'Clubs'),
                Card(2, 'Clubs'),
                Card(3, 'Clubs'),
                Card(4, 'Clubs'),
                Card(5, 'Clubs'),
                Card(6, 'Clubs'),
                Card(7, 'Clubs'),
                Card(8, 'Clubs'),
                Card(9, 'Clubs'),
                Card(10, 'Clubs'),
                Card(11, 'Clubs'),
                Card(12, 'Clubs'),
                Card(13, 'Clubs')]

    def GetJokerDeck():
        """Provides a with jokers based on the standard deck"""
        return Card.GetStandardDeck() + [Card(0, None), Card(0, None)]
