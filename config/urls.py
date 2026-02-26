""" Urls of the modules define here... """

# Swagger API...
from ..config.swagger import api

# All Namespaces...
from ..deals.handler import deal_namespace
from ..bot.handler import bot_namespace





# Adding the namespaces
class URLs:
    """ All application namespaces will be declare here... """

    @staticmethod
    def add_namespaces():
        """ Function for adding namespaces... """

        api.add_namespace(deal_namespace)
        api.add_namespace(bot_namespace)
