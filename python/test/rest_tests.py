from __future__ import print_function
import json
import logging
import subprocess
import unittest
from test_operators import DelayedTupleSourceWithLastTuple

from streamsx import rest
from streamsx.topology import topology, context

credentials_file_name = 'sws_credentials.json'
logger = logging.getLogger('streamsx.test.rest_test')
class TestRestFeatures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """
        Initialize the logger and get the SWS username, password, and REST URL.
        :return: None
        """
        cls.logger = logger

        # Get credentials from creds file.
        creds_file = open(credentials_file_name, mode='r')
        try:
            creds_json = json.loads(creds_file.read())
            cls.sws_username = creds_json['username']
            cls.sws_password = creds_json['password']
        except:
            cls.logger.exception("Error while reading and parsing " + credentials_file_name)
            raise

        # Get the SWS REST URL
        try:
            process = subprocess.Popen(['streamtool', 'geturl', '--api'],
                                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            cls.sws_rest_api_url = process.stdout.readline().strip().decode('utf-8')
        except:
            cls.logger.exception("Error getting SWS rest api url via streamtool")
            raise

    def test_ensure_correct_rest_module(self):
        # Ensure that the rest module being tested is from streamsx.utility
        self.assertTrue('streamsx.utility' in rest.__file__)

    def test_username_and_password(self):
        # Ensure, at minimum, that the StreamsContext can connect and retrieve valid data from the SWS resources path
        ctxt = rest.StreamsContext(self.sws_username, self.sws_password, self.sws_rest_api_url)
        resources = ctxt.get_resources()
        self.logger.debug("Number of retrieved resources is: " + str(len(resources)))
        self.assertGreater(len(resources), 0, msg="Returned zero resources from the \"resources\" endpoint.")

    def test_basic_view_support(self):
        top = topology.Topology('basicViewTest')
        # Send only one tuple
        view = top.source(DelayedTupleSourceWithLastTuple(['hello'], 20)).view()
        self.logger.debug("Begging compilation and submission of basic_view_support topology.")
        context.submit(context.ContextTypes.DISTRIBUTED, top, username = self.sws_username, password=self.sws_password)

        queue = view.start_data_fetch()

        try:
            view_tuple_value = queue.get(block=True, timeout=20.0)
        except:
            view.stop_data_fetch()
            logger.exception("Timed out while waiting for tuple.")
            raise

        self.logger.debug("Returned view value in basic_view_support is " + view_tuple_value)
        self.assertTrue(view_tuple_value.startswith('hello'))
