#!/usr/bin/env python3
"""
EC2 Deployment Script for Homemade Pickles & Snacks
This script launches an EC2 instance with the Flask application.
"""

import boto3
import base64
from botocore.exceptions import ClientError

def launch_ec2_instance():
    """Launch EC2 instance with the Flask application"""
    ec2 = boto3.client('ec2', region_name='ap-south-1')
    
    # Read user data script
    try:
        with open('user-data.sh', 'r') as f:
            user_data = f.read()
    except FileNotFoundError:
        print("❌ user-data.sh file not found")
        return None
    
    try:
        # Get the latest Amazon Linux 2 AMI
        images = ec2.describe_images(
            Owners=['amazon'],
            Filters=[
                {'Name': 'name', 'Values': ['amzn2-ami-hvm-*-x86_64-gp2']},
                {'Name': 'state', 'Values': ['available']}
            ]
        )
        
        # Sort by creation date and get the latest
        latest_ami = sorted(images['Images'], key=lambda x: x['CreationDate'], reverse=True)[0]
        ami_id = latest_ami['ImageId']
        
        # Launch instance
        response = ec2.run_instances(
            ImageId=ami_id,
            MinCount=1,
            MaxCount=1,
            InstanceType='t2.micro',  # Free tier eligible
            KeyName='your-key-pair',  # Replace with your key pair name
            SecurityGroups=['pickle-app-sg'],
            IamInstanceProfile={'Name': 'PickleAppProfile'},
            UserData=user_data,
            TagSpecifications=[
                {
                    'ResourceType': 'instance',
                    'Tags': [
                        {'Key': 'Name', 'Value': 'Pickle-App-Server'},
                        {'Key': 'Project', 'Value': 'HomemadePickles'}
                    ]
                }
            ]
        )
        
        instance_id = response['Instances'][0]['InstanceId']
        print(f"✅ EC2 instance launched: {instance_id}")
        
        # Wait for instance to be running
        print("⏳ Waiting for instance to be running...")
        waiter = ec2.get_waiter('instance_running')
        waiter.wait(InstanceIds=[instance_id])
        
        # Get instance details
        instances = ec2.describe_instances(InstanceIds=[instance_id])
        instance = instances['Reservations'][0]['Instances'][0]
        public_ip = instance.get('PublicIpAddress')
        
        print(f"🌐 Instance is running!")
        print(f"Public IP: {public_ip}")
        print(f"Access your app at: http://{public_ip}")
        
        return instance_id
        
    except ClientError as e:
        print(f"❌ Error launching EC2 instance: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None

def main():
    """Main deployment function"""
    print("🚀 Deploying Homemade Pickles & Snacks to EC2...")
    
    # Launch EC2 instance
    instance_id = launch_ec2_instance()
    
    if instance_id:
        print("\n📋 Deployment Summary:")
        print(f"Instance ID: {instance_id}")
        print("\n📝 Next Steps:")
        print("1. SSH into the instance")
        print("2. Copy your application files to /opt/pickle-app/")
        print("3. Start the service: sudo systemctl start pickle-app")
        print("4. Check status: sudo systemctl status pickle-app")
    else:
        print("❌ Deployment failed")

if __name__ == "__main__":
    main()