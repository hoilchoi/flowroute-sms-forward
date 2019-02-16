# flowroute-sms-forward

Receive inbound SMS to Flowroute DID and forward to cell phone or other number.  


## Prerequisites:

AWS account.

Flowroute account.

## VM Provision

This does not actually require VM.  Can be done from local machine. 

However, if preferred to use VM, vagrant can be used to create a quick app server to deploy.
```shell
$ vagrant up
```
Once VM is up and provisioned, you can login to VM.
```shell
$ vagrant ssh
```

## Create User in AWS

From IAM service in AWS, add user.  

- Username: Any
- Access Type: Programmatic Access

Set Permission:

1. Select `Attach existing policies directly`

2. Click `Create policy`

It will open new tab or window
- Click `Json` tab
- Copy and paste policy from `user_policy.json`
- Click `Review policy`
- Add name and description, then click `Create policy`

3. When done, go back to `Add User` page and click refresh button.

4. Search for the policy created and apply it.
- Tags: optional.

When user is created, you will receive Access Key ID and Secret Access Key.

Use these keys to create `credential` file in your environment's ~/.aws folder as below.
```
[default]
aws_access_key_id = [API ACCESS KEY]
aws_secret_access_key = [API SECRET KEY]
```

## Config.py
Update `config.py.sample` and rename to `config.py`
```
SMS_URL = "https://api.flowroute.com/v2.1/messages"
API_KEY = "FLOWROUTE_API_KEY"
API_SECRET = "FLOWROUTE_API_SECRET"
FROM_NUMBER = "11-DIGIT TO BE DISPLAYED AS SENDER"
FORWARD_NUMBER = "11-DIGIT DESTINATION NUMBER"
```

## Deploy
Deploy service using sls command:
```shell
$ sls deploy
```

It will give API endpoint to use in your Flowroute account's PREFERENCE -> API Control.  

Add the endpoint to SMS callback.

Now any SMS to your Flowroute DID will be forwarded to your `FORWARD_NUMBER = "11-DIGIT DESTINATION NUMBER"` added above.  

VM can be destroyed if you wish. 
```shell
$ vagrant destroy
```
