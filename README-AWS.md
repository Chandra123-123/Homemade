# AWS Infrastructure Setup for Homemade Pickles & Snacks

This document provides instructions for setting up the AWS infrastructure required for the Flask application.

## Prerequisites

1. AWS CLI configured with appropriate credentials
2. Python 3.x installed
3. boto3 library installed (`pip install boto3`)

## AWS Services Used

- **DynamoDB**: Stores order information
- **SNS**: Sends order notifications
- **IAM**: Manages permissions for EC2 instance
- **EC2**: Hosts the Flask application

## Setup Instructions

### 1. Create AWS Resources

Run the setup script to create all necessary AWS resources:

```bash
python aws-setup.py
```

This script will create:
- DynamoDB table: `PickleOrders`
- SNS topic: `OrderConfirmations`
- IAM role: `PickleAppRole` with necessary permissions
- Security group: `pickle-app-sg` (ports 80, 22)

### 2. Update SNS Topic ARN

After running the setup script, update the `SNS_TOPIC_ARN` in `app.py` with the actual ARN provided by the script.

### 3. Deploy to EC2 (Optional)

To deploy the application to EC2:

1. Create an EC2 key pair in the AWS console
2. Update the `KeyName` in `deploy.py` with your key pair name
3. Run the deployment script:

```bash
python deploy.py
```

### 4. Manual EC2 Setup

If you prefer manual setup:

1. Launch an EC2 instance (Amazon Linux 2)
2. Attach the `PickleAppProfile` instance profile
3. Use the security group `pickle-app-sg`
4. Copy the `user-data.sh` script content to User Data
5. SSH into the instance and deploy your application files

## Application Deployment

1. Copy all application files to `/opt/pickle-app/` on the EC2 instance
2. Install dependencies: `pip3 install -r requirements.txt`
3. Start the application service: `sudo systemctl start pickle-app`
4. Enable auto-start: `sudo systemctl enable pickle-app`

## Testing

1. Access the application via the EC2 public IP address
2. Test order placement to verify DynamoDB integration
3. Check SNS notifications by subscribing to the topic

## Security Considerations

- The security group allows HTTP (port 80) and SSH (port 22) access
- IAM role has minimal permissions for DynamoDB and SNS
- Consider using HTTPS in production
- Restrict SSH access to specific IP ranges

## Monitoring

- CloudWatch logs are available for the EC2 instance
- DynamoDB and SNS metrics are available in CloudWatch
- Consider setting up CloudWatch alarms for monitoring

## Cost Optimization

- Use t2.micro instances (free tier eligible)
- DynamoDB is configured with on-demand billing
- SNS charges per message sent
- Monitor usage through AWS Cost Explorer

## Troubleshooting

1. Check EC2 instance logs: `sudo journalctl -u pickle-app`
2. Verify IAM permissions if AWS service calls fail
3. Check security group settings for connectivity issues
4. Ensure DynamoDB table exists and is accessible

## Cleanup

To remove all resources:
1. Terminate EC2 instances
2. Delete DynamoDB table
3. Delete SNS topic
4. Remove IAM role and policies
5. Delete security group