import boto3
import paramiko
import os
import time

# AWS credentials are passed via environment variables
ec2 = boto3.resource('ec2', aws_region='us-east-1')
instance = ec2.create_instances(
    ImageId=os.getenv('AWS_AMI_ID'),
    MinCount=1, MaxCount=1,
    InstanceType=os.getenv('AWS_INSTANCE_TYPE', 't2.micro'),
    KeyName=os.getenv('AWS_KEY_NAME'),
    SecurityGroups=[os.getenv('AWS_SECURITY_GROUP')],
)[0]

instance.wait_until_running()
instance.load()
ip = instance.public_ip_address

# Wait for SSH to become available
time.sleep(30)

# SSH setup
key = paramiko.RSAKey.from_private_key_file(io.StringIO(os.getenv('SSH_PRIVATE_KEY')))
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(ip, username=os.getenv('SSH_USERNAME', 'ubuntu'), pkey=key)

# Run commands
cmds = [
    'cd /home/ubuntu',
    'cd devops-midterm && git pull && docker compose up -d'
]
for cmd in cmds:
    ssh.exec_command(cmd)
    time.sleep(10)  # Allow time for setup

# Test services
for port in [5173, 8080]:
    stdin, stdout, stderr = ssh.exec_command(f'curl -s -o /dev/null -w "%{{http_code}}" localhost:{port}')
    if stdout.read().decode().strip() != '200':
        print(f'Port {port} check failed')
        break
else:
    print('Smoke test passed')

# Terminate instance
instance.terminate()
ssh.close()