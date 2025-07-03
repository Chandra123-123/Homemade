#!/usr/bin/env python3
"""
AWS Infrastructure Setup Script for Homemade Pickles & Snacks
This script creates the necessary AWS resources for the application.
"""

import boto3
import json
from botocore.exceptions import ClientError

def create_dynamodb_tables():
    """Create DynamoDB tables for storing orders and users"""
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    
    # Create Orders table
    try:
        orders_table = dynamodb.create_table(
            TableName='PickleOrders',
            KeySchema=[
                {
                    'AttributeName': 'order_id',
                    'KeyType': 'HASH'
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'order_id',
                    'AttributeType': 'S'
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        orders_table.wait_until_exists()
        print("✅ DynamoDB table 'PickleOrders' created successfully")
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            print("✅ DynamoDB table 'PickleOrders' already exists")
        else:
            print(f"❌ Error creating PickleOrders table: {e}")
    
    # Create Users table
    try:
        users_table = dynamodb.create_table(
            TableName='PickleUsers',
            KeySchema=[
                {
                    'AttributeName': 'email',
                    'KeyType': 'HASH'
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'email',
                    'AttributeType': 'S'
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        users_table.wait_until_exists()
        print("✅ DynamoDB table 'PickleUsers' created successfully")
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            print("✅ DynamoDB table 'PickleUsers' already exists")
            return True
        else:
            print(f"❌ Error creating PickleUsers table: {e}")
            return False

def create_sns_topic():
    """Create SNS topic for order notifications"""
    sns = boto3.client('sns', region_name='us-east-1')
    
    try:
        response = sns.create_topic(Name='OrderConfirmations')
        topic_arn = response['TopicArn']
        print(f"✅ SNS topic 'OrderConfirmations' created: {topic_arn}")
        return topic_arn
        
    except ClientError as e:
        print(f"❌ Error creating SNS topic: {e}")
        return None

def create_iam_role():
    """Create IAM role for EC2 instance"""
    iam = boto3.client('iam', region_name='us-east-1')
    
    # Trust policy for EC2
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "ec2.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    # IAM policy for DynamoDB and SNS access
    permissions_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "dynamodb:PutItem",
                    "dynamodb:GetItem",
                    "dynamodb:UpdateItem",
                    "dynamodb:DeleteItem",
                    "dynamodb:Query",
                    "dynamodb:Scan"
                ],
                "Resource": "arn:aws:dynamodb:us-east-1:*:table/PickleOrders"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "sns:Publish"
                ],
                "Resource": "arn:aws:sns:us-east-1:*:OrderConfirmations"
            }
        ]
    }
    
    try:
        # Create IAM role
        role_response = iam.create_role(
            RoleName='PickleAppRole',
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description='Role for Pickle App EC2 instance'
        )
        
        # Create and attach policy
        iam.put_role_policy(
            RoleName='PickleAppRole',
            PolicyName='PickleAppPolicy',
            PolicyDocument=json.dumps(permissions_policy)
        )
        
        # Create instance profile
        iam.create_instance_profile(InstanceProfileName='PickleAppProfile')
        iam.add_role_to_instance_profile(
            InstanceProfileName='PickleAppProfile',
            RoleName='PickleAppRole'
        )
        
        print("✅ IAM role 'PickleAppRole' and instance profile created")
        return role_response['Role']['Arn']
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'EntityAlreadyExists':
            print("✅ IAM role 'PickleAppRole' already exists")
            return f"arn:aws:iam::{boto3.client('sts').get_caller_identity()['Account']}:role/PickleAppRole"
        else:
            print(f"❌ Error creating IAM role: {e}")
            return None

def get_security_group():
    """Create or get security group for web application"""
    ec2 = boto3.client('ec2', region_name='us-east-1')
    
    try:
        # Try to find existing security group
        response = ec2.describe_security_groups(
            Filters=[
                {'Name': 'group-name', 'Values': ['pickle-app-sg']}
            ]
        )
        
        if response['SecurityGroups']:
            sg_id = response['SecurityGroups'][0]['GroupId']
            print(f"✅ Using existing security group: {sg_id}")
            return sg_id
        
        # Create new security group
        vpc_response = ec2.describe_vpcs(Filters=[{'Name': 'isDefault', 'Values': ['true']}])
        vpc_id = vpc_response['Vpcs'][0]['VpcId']
        
        sg_response = ec2.create_security_group(
            GroupName='pickle-app-sg',
            Description='Security group for Pickle App',
            VpcId=vpc_id
        )
        
        sg_id = sg_response['GroupId']
        
        # Add inbound rules
        ec2.authorize_security_group_ingress(
            GroupId=sg_id,
            IpPermissions=[
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 80,
                    'ToPort': 80,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                },
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 22,
                    'ToPort': 22,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                }
            ]
        )
        
        print(f"✅ Security group created: {sg_id}")
        return sg_id
        
    except ClientError as e:
        print(f"❌ Error with security group: {e}")
        return None

def main():
    """Main setup function"""
    print("🚀 Setting up AWS infrastructure for Homemade Pickles & Snacks...")
    
    # Create DynamoDB tables
    tables_created = create_dynamodb_tables()
    
    # Create SNS topic
    topic_arn = create_sns_topic()
    
    # Create IAM role
    role_arn = create_iam_role()
    
    # Get security group
    sg_id = get_security_group()
    
    print("\n📋 Setup Summary:")
    print(f"DynamoDB Table: PickleOrders")
    print(f"SNS Topic ARN: {topic_arn}")
    print(f"IAM Role: PickleAppRole")
    print(f"Security Group: {sg_id}")
    
    if topic_arn:
        print(f"\n⚠️  Update app.py with your SNS Topic ARN:")
        print(f"SNS_TOPIC_ARN = '{topic_arn}'")

if __name__ == "__main__":
    main()