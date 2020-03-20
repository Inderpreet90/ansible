#!/usr/bin/python
# Copyright (c) 2020 Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: aws_transfer_server
'''

EXAMPLES = '''
# Note: These examples do not set authentication details, see the AWS Guide for details.

# Create an AWS SFTP server
- aws_transfer_server:
'''

RETURN = '''
'''


from ansible.module_utils.aws.core import AnsibleAWSModule
from ansible.module_utils.ec2 import get_aws_connection_info, ec2_argument_spec, boto3_conn
from ansible.module_utils.ec2 import ansible_dict_to_boto3_filter_list, camel_dict_to_snake_dict, HAS_BOTO3

try:
    import botocore.exceptions
except ImportError:
    pass  # caught by AnsibleAWSModule


# https://docs.aws.amazon.com/transfer/latest/userguide/API_CreateServer.html
# https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/transfer.html#Transfer.Client.create_server
def ensure_present(client, module):
    server = get_server(client, module)

    if server:
        pass
        # if set(server['resourcesVpcConfig']['subnetIds']) != set(subnets):
        #     module.fail_json(msg="Cannot modify subnets of existing cluster")
        # if set(cluster['resourcesVpcConfig']['securityGroupIds']) != set(groups):
        #     module.fail_json(msg="Cannot modify security groups of existing cluster")
        # if module.params.get('version') and module.params.get('version') != cluster['version']:
        #     module.fail_json(msg="Cannot modify version of existing cluster")

    if module.check_mode:
        module.exit_json(changed=True)

    try:
        params = dict(EndpointType=module.params('endpoint_type'),
            IdentityProviderType=module.params('identity_provider_type'),
            LoggingRole=modules.params('logging_role'),
            Tags=module.params('tags'))
        if module.params['endpoint_type'] == 'VPC':
            params['EndpointDetails'] = dict(
                AddressAllocationIds=[],
                SubnetIds=[],
                VpcEndpointId='',
                VpcId='')
        if module.params['identity_provider_type'] == 'API_GATEWAY':
            params['IdentityProviderDetails'] = dict(
                Url=module.params['identity_provider_url'],
                InvocationRole=module.params['identity_provider_role'])
        if 'host_key' in module.params:
            params['HostKey'] = module.params('host_key')
        server = client.create_server(**params)
    except botocore.exceptions.EndpointConnectionError as e:
        module.fail_json(msg="Region %s is not supported by Transfer for SFTP" %
                         client.meta.region_name)
    except (botocore.exceptions.BotoCoreError, botocore.exceptions.ClientError) as e:
        module.fail_json_aws(e, msg="Couldn't create server %s" % name)

    if wait:
        wait_until_server_active(client, module)
        # Ensure that fields that are only available for active clusters are
        # included in the returned value
        server = get_server(client, module)

    module.exit_json(changed=True, **camel_dict_to_snake_dict(server))


def ensure_absent(client, module):
    pass


def get_server(client, module):
    if 'server_id' not in module.params:
        return None


def wait_until_server_active(client, module):
    name = module.params.get('name')
    wait_timeout = module.params.get('wait_timeout')

    waiter = get_waiter(client, 'server_active')
    attempts = 1 + int(wait_timeout / waiter.config.delay)
    waiter.wait(name=name, WaiterConfig={'MaxAttempts': attempts})


def main():
    argument_spec = dict(
        endpoint_type=dict(type='str', choices=['PUBLIC', 'VPC', 'VPC_ENDPOINT']),
        #custom_hostname=dict(type='str'),
        host_key=dict(type='str'),
        identity_provider_type=dict(type='str', default='SERVICE_MANAGED',
                                    choices=['SERVICE_MANAGED', 'API_GATEWAY'])
        identity_provider_url=dict(type='str'),
        identity_provider_role=dict(type='str'),
        logging_role=dict(type='str'),
        purge_tags=dict(type='bool', default=True),
        server_id=dict(type='str'),
        state=dict(choices=['absent', 'present'], default='present'),
        #endpoint_subnet_ids=dict(type='list'),
        subnet_ids=dict(type='list'),
        vpc_id=dict(type='str'),
        vpc_endpoint_id=(type='str'),
        wait=dict(type='bool', default=False),
        wait_timeout=dict(type='int',default=1200)
    )

    module = AnsibleAWSModule(
        argument_spec=argument_spec,
        required_if=[
            ['state', 'present', ['endpoint_type', 'identity_provider_type',
                                  'logging_role']],
            ['identity_provider_type', 'API_GATEWAY', ['identity_provider_url',
                                                       'identity_provider_role']],
            ['state', 'absent', ['server_id']],
        ],
        supports_check_mode=True,
    )

    # if not module.botocore_at_least("1.10.32"):
    #     module.fail_json(msg="aws_eks_cluster module requires botocore >= 1.10.32")

    client = module.client('transfer')

    if module.params.get('state') == 'present':
        ensure_present(client, module)
    else:
        ensure_absent(client, module)


if __name__ == '__main__':
    main()
