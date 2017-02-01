# Licensed Materials - Property of IBM
# Copyright IBM Corp. 2016
import requests
import os
import json
import logging

from .rest_primitives import Domain, Instance, Installation, Resource, StreamsRestClient
from pprint import pformat
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

logger = logging.getLogger('streamsx.rest')


class StreamsContext:
    def __init__(self, username=None, password=None, resource_url=None, config=None):
        # manually specify username, password, and resource_url
        if username and password and resource_url:
            self.rest_client = StreamsRestClient(username, password, resource_url)
            self.resource_url = resource_url

        # Connect to Bluemix service using VCAP
        elif config:
            vcap_services = StreamsContext._get_vcap_services(config)
            credentials = StreamsContext._get_credentials(config, vcap_services)

            # Obtain the streams SWS REST URL
            resources_url = credentials['rest_url'] + credentials['resources_path']
            try:
                response = requests.get(resources_url, auth=(username, password)).json()
            except:
                logger.exception("Error while retrieving SWS REST url from: " + resources_url)
                raise

            rest_api_url = response['streams_rest_url'] + '/resources'

            # Create rest connection to remote Bluemix SWS
            self.rest_client = StreamsRestClient(credentials['userid'], credentials['password'], rest_api_url)
            self.resource_url = rest_api_url
        else:
            logger.error("Invalid arguments for StreamsContext.__init__: must supply either a BlueMix VCAP Services or "
                         "a username, password, and resource url.")
            raise ValueError("Must supply either a BlueMix VCAP Services or a username, password, and resource url"
                             " to the StreamsContext constructor.")

    def get_domains(self):
        domains = []
        for resource in self.get_resources():
            # Get list of domains
            if resource.name == "domains":
                for json_domain in resource.get_resource()['domains']:
                    domains.append(Domain(json_domain, self.rest_client))
        return domains

    def get_instances(self):
        instances = []
        for resource in self.get_resources():
            # Get list of domains
            if resource.name == "instances":
                for json_rep in resource.get_resource()['instances']:
                    instances.append(Instance(json_rep, self.rest_client))
        return instances

    def get_installations(self):
        installations = []
        for resource in self.get_resources():
            # Get list of domains
            if resource.name == "installations":
                for json_rep in resource.get_resource()['installations']:
                    installations.append(Installation(json_rep, self.rest_client))
        return installations

    def get_resources(self):
        resources = []
        json_resources = self.rest_client.make_request(self.resource_url)['resources']
        for json_resource in json_resources:
            resources.append(Resource(json_resource, self.rest_client))
        return resources

    def __str__(self):
        return pformat(self.__dict__)

    @staticmethod
    def _get_vcap_services(config):
        # Attempt to retrieve from config
        try:
            vs = config[ConfigParams.VCAP_SERVICES]
        except KeyError:
            # If that fails, try to get it from the environment
            try:
                vs = os.environ['VCAP_SERVICES']
            except KeyError:
                raise ValueError(
                    "VCAP_SERVICES information must be supplied in config[ConfigParams.VCAP_SERVICES] or as environment variable 'VCAP_SERVICES'")

        # If it was passed to config as a dict, simply return it
        if isinstance(vs, dict):
            return vs
        try:
            # Otherwise, if it's a string, try to load it as json
            vs = json.loads(vs)
        except json.JSONDecodeError:
            # If that doesn't work, attempt to open it as a file path to the json config.
            try:
                with open(vs) as vcap_json_data:
                    vs = json.load(vcap_json_data)
            except:
                raise ValueError("VCAP_SERVICES information is not JSON or a file containing JSON:", vs)
        return vs

    @staticmethod
    def _get_credentials(config, vcap_services):
        # Get the credentials for the selected service, from VCAP_SERVICES config param
        try:
            service_name = config[ConfigParams.SERVICE_NAME]
        except KeyError:
            raise ValueError("Service name was not supplied in config[ConfigParams.SERVICE_NAME.")

        # Get the service corresponding to the SERVICE_NAME
        services = vcap_services['streaming-analytics']
        creds = None
        for service in services:
            if service['name'] == service_name:
                creds = service['credentials']
                break

        # If no corresponding service is found, error
        if creds is None:
            raise ValueError("Streaming Analytics service " + service_name + " was not found in VCAP_SERVICES")
        return creds


def get_view_obj(_view, rc):
    for domain in rc.get_domains():
        for instance in domain.get_instances():
            for view in instance.get_views():
                if view.name == _view.name:
                    return view
    return None


class ConfigParams(object):
    """
    Configuration options which may be used as keys in the config parameter of the StreamsContext constructor.

    VCAP_SERVICES - a json object containing the VCAP information used to submit to Bluemix
    SERVICE_NAME - the name of the streaming analytics service to use from VCAP_SERVICES.
    """
    VCAP_SERVICES = 'topology.service.vcap'
    SERVICE_NAME = 'topology.service.name'
