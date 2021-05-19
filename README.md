## Discord To Playlist
Parses every message (or a desired range of messages) containing a valid YouTube video URL from a guild text channel and converts it to a YouTube Playlist.

![Example](https://i.imgur.com/T6dJCV7.png)

## Requirements
Stupidly long because I don't care to create a public App and Google API sucks.
- **Install the required packages**   
Simply run `pip install -r requirements.txt` in the CWD.   

- **Download the source code**   
Yeah.

- **Configure the consent screen**   
*"To create an OAuth client ID, you must first set a product name on the consent screen."*   
Go to [https://console.cloud.google.com/apis](https://console.cloud.google.com/apis)      
Click on "CONFIGURE CONSENT SCREEN".
Select "External" as the user type.   
Fill the required (*) fields.   
Ignore the Scopes section.   
Add yourself as a test user.

- **Create a Google OAuth 2.0 Client ID**   
Go back to [https://console.cloud.google.com/apis](https://console.cloud.google.com/apis)     
Go to the Credentials tab.   
Click "CREATE CREDENTIALS".   
Select "OAuth client ID".   
You must configure the consent screen if you haven't already.
Select "Desktop app" as the application type.   
Pick whatever you would like your app to be called. Something like "Discord To Playlist" works just fine.   
Go back to the Credentials tab and you should now see your app in the "OAuth 2.0 Client IDs" section.   
Click the download button on the right and save the .json file as "credentials.json" on the source code folder.

The **credentials.json** file should look something like this (but [minified](https://en.wikipedia.org/wiki/Minification_(programming))):
```json
{
    "installed": {
        "client_id": "8267...............................vu50.apps.googleusercontent.com",
        "project_id":"your-epic-project-id",
        "auth_uri":"https://accounts.google.com/o/oauth2/auth",
        "token_uri":"https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url":"https://www.googleapis.com/oauth2/v1/certs",
        "client_secret":"SgNJ...........xDxc",
        "redirect_uris": [
            "urn:ietf:wg:oauth:2.0:oob",
            "http://localhost"
        ]
    }
}
```
- **Copy your Discord user token**   
Using a user Discord token is considered a self-bot and can get your account banned and blablabla, Discord is fucking stupid   
On the desktop app press CTRL+SHIFT+i and the console will pop-up   
Go to "Application > Local Storage > https://discord.com" and scroll down    
Press CTRL+r to restart your application and the "token" key should appear at the bottom  
Copy the value and save it somewhere   
Don't share it with anyone or you will have to reset your password and do everything again to get a new token

## Arguments
| Argument                    | Type | Required | Default            | Help                                                                                 |
|-----------------------------|------|----------|--------------------|--------------------------------------------------------------------------------------|
| -t, --token                 | str  | True     | None               | User secret Discord token                                                            |
| -tt, --token_type           |  str | False    | User               | Token type. Either "User", "Bearer" or "Bot"                                         |
| -cid, --channel_id          | int  | True     | None               | Valid text channel ID                                                                |
| -sid, --start_id            | int  | True     | None               | Start message ID. MUST be greater than --end_id                                      |
| -eid, --end_id              | int  | True     | None               | End message ID. MUST be less than --start_id                                         |
| -ytc, --youtube_credentials | str  | False    | ./credentials.json | YouTube APP .json credentials                                                        |
| -pid, --playlist_id         | str  | True     | None               | YouTube playlist ID youtube.com/playlist?list=<this_is_your_playlist_id> |

## Usage
After downloading the source code and doing all that Google and Discord stuff you can simply:
```bash
$ py main.py -t token -cid channel -sid start -eid end -pid playlist
```
Check "Arguments" above or type `--help` for more info.

You will be prompted to authenticate access to the app. Simply follow the link and accept everything until you get a token. Paste the token in the console and you are done. After that, you won't be asked to authenticate again.  

**(You won't be able to authenticate if you haven't added yourself a test user when configuring the consent screen of your app)**

## Notes  
- The messages are parsed going upwards (from last to first) so that's why `--start_id` must be greater than `--end_id`.  
An over-simplified usage example would be:
```none
Example Discord Chat:
Channel id 1234567890
Message id 1: url_1
Message id 2: url_2
Message id 3: url_3
Message id 4: url_4
Message id 5: url_5

Example Script Usage:
$ py main.py -t my_token -cid 1234567890 -sid 5 -eid 1 -pid my_playlist

Expected Result:
All 5 urls are added to my_playlist
```

- The Google API library does not save the credentials so [pickle](https://docs.python.org/3.6/library/pickle.html) is used to save them and run the authentication proccess automatically. That's why a credentials.dat file will be automatically created after using the script for the first time. Just don't delete it or you will be asked to manually authenticate again.

- The script has not been yet tested using Bot or Bearer tokens but it *should?* work just fine.  

- There is no way of checking if the message IDs are valid using the Discord API so the script will simply not work if you input an invalid message ID.  
(There actually is a way of checking it but surprise! `{'message': 'Only bots can use this endpoint', 'code': 20002}`).  

- The YouTube API will throw HTTP/403 Forbidden if you exceed your API quota and you will have to wait x amount of hours to make a request again.  
I have no idea how to check how much quota there is left before exceeding it nor I do know how long is the cooldown so if someone could help me on that it would be nice. Making any request reduces the quota you have left even if its just for checking if the video already exists in the playlist or if the video ID is valid, so make sure to not try to add videos that are already in the playlist or videos that have been deleted etc.

## TODO
Automatically create playlists. (API request works, too lazy to implement it with arguments)
