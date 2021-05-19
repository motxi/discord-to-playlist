import os
import re
import pickle
import requests
from time import sleep
from colorama import init, Fore, Style
from typing import Generator, List, Optional, Dict, Any
from argparse import ArgumentParser
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request

init(autoreset=True)

class RequestError(Exception): pass

class Constants(object):
    HTTP_STATUS_CODES = {
        400: "Bad Request",
        401: "Unauthorized",
        403: "Forbidden",
        404: "Not Found",
        405: "Method Not Allowed",
        408: "Request Timeout",
        429: "Too Many Requests",
        500: "Internal Server Error",
        501: "Not Implemented",
        502: "Bad Gateway",
        503: "Service Unavailable",
        504: "Gateway Timeout"
    }
    DISCORD_API_BASE_URL = "https://discord.com/api/v9"
    DISCORD_API_MESSAGE_LIMIT = 100
    DISCORD_API_RATE_LIMIT = 5
    YOUTUBE_SCOPE_URLS = ["https://www.googleapis.com/auth/youtube"]
    YOUTUBE_API_SERVICE_NAME = "youtube"
    YOUTUBE_API_VERSION = "v3"

class RequestAPI(Constants):
    def __init__(self, authorization: str) -> None:
        self.authorization = authorization

    def _request(self, method: str, base_url: str, request_url: str, params: Optional[Dict[str, Any]] = {}) -> requests.Response:
        session = requests.Session()
        session.headers.update({
            "Authorization": self.authorization
        })

        for _ in range(Constants.DISCORD_API_RATE_LIMIT):
            request = session.request(method, f"{base_url}{request_url}", params)

            if request.status_code == 200:
                return request
            elif request.status_code in Constants.HTTP_STATUS_CODES:
                raise RequestError(f"{Fore.RED}{Style.BRIGHT}[D2P] An error occurred while trying to request to the API. Error: [{request.status_code}] {self.HTTP_STATUS_CODES[request.status_code]}")
            else:
                raise RequestError(f"{Fore.RED}{Style.BRIGHT}[D2P] An error occurred while trying to request to the API. Error status code: {request.status_code}")

class Discord(RequestAPI, Constants):
    def __init__(self, token_type: str, token: str) -> None:
        self.token_type = token_type.capitalize()
        self.token = token
        
        sanitized_token = f"{self.token_type} {self.token}" if self.token_type != "User" else self.token
        self.api = RequestAPI(sanitized_token)
    
    # GET https://discord.com/developers/docs/resources/channel#get-channel
    def _check_channel(self, channel_id: int) -> Dict[str, Any]:
        return self.api._request(
            method="get",
            base_url=Constants.DISCORD_API_BASE_URL,
            request_url=f"/channels/{channel_id}"
        ).json()

    # GET https://discord.com/developers/docs/resources/channel#get-channel-messages
    # https://github.com/denebu/discord-chat-exporter/blob/550c9a8a9bdf42be0d23832e81237b8eb7e0d63a/discord-chat-exporter.py#L56
    def generate_messages(self, channel_id: int, start_message_id: int, end_message_id: int) -> Generator[Dict[str, Any], None, None]:
        if self._check_channel(channel_id)["type"] in [0, 5]:
            current_message_id = start_message_id + 1

            while True:
                request = self.api._request(
                    method="get",
                    base_url=Constants.DISCORD_API_BASE_URL,
                    request_url=f"/channels/{channel_id}/messages",
                    params={
                        "before": current_message_id,
                        "limit": Constants.DISCORD_API_MESSAGE_LIMIT,
                    }
                )

                messages = request.json()
                messages = list(filter(lambda message: int(message["id"]) >= end_message_id, messages))

                yield messages

                if len(messages) < Constants.DISCORD_API_MESSAGE_LIMIT:
                    break

                current_message_id = int(messages[-1]["id"])
        else:
            raise RequestError(f"{Fore.RED}{Style.BRIGHT}[D2P] Invalid channel type. Channel ID must point to a valid GUILD_TEXT or GUILD_NEWS type channel")

    def parse_messages(self, generator: Generator[Dict[str, Any], None, None]) -> List[str]:
        messages = []

        for message_object_list in list(generator):
            for message_object in message_object_list:
                com_regex = re.search(r"(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=(.+)", message_object["content"])
                be_regex = re.search(r"(?:https?:\/\/)?youtu\.be\/(.+)", message_object["content"])

                if com_regex:
                    messages.append(com_regex[1])
                elif be_regex:
                    messages.append(be_regex[1])
                else:
                    continue
        
        return list(dict.fromkeys(messages[::1]))

class YouTube(Constants):
    def __init__(self, client_secrets_file: str = "credentials.json") -> None:
        self.client_secrets_file = client_secrets_file

    # https://stackoverflow.com/questions/52085054
    # https://developers.google.com/identity/protocols/oauth2
    def _authenticate_service(self) -> Resource:
        if not os.path.exists("credentials.dat"):
            flow = InstalledAppFlow.from_client_secrets_file(
                client_secrets_file=self.client_secrets_file,
                scopes=Constants.YOUTUBE_SCOPE_URLS
            )

            credentials = flow.run_local_server()

            with open("credentials.dat", "wb") as credentials_dat:
                pickle.dump(credentials, credentials_dat)
        else:
            with open("credentials.dat", "rb") as credentials_dat:
                credentials = pickle.load(credentials_dat)
        
        if credentials.expired:
            credentials.refresh(Request())

        return build(
            serviceName=Constants.YOUTUBE_API_SERVICE_NAME,
            version=Constants.YOUTUBE_API_VERSION,
            credentials=credentials
        )

    # https://stackoverflow.com/questions/18804904
    # GET https://developers.google.com/youtube/v3/docs/playlistItems/list
    def _get_playlist_content(self, playlist_id: str) -> List[str]:
        playlist = self._authenticate_service().playlistItems().list(
            part="snippet",
            playlistId=playlist_id,
            maxResults="50"
        ).execute()

        next_page_token = playlist.get("nextPageToken")
        while "nextPageToken" in playlist:
            next_page = self._authenticate_service().playlistItems().list(
                part="snippet",
                playlistId=playlist_id,
                maxResults="50",
                pageToken=next_page_token
            ).execute()

            playlist["items"] = playlist["items"] + next_page["items"]

            if "nextPageToken" not in next_page:
                playlist.pop("nextPageToken", None)
            else:
                next_page_token = next_page["nextPageToken"]
        
        video_ids = []
        for item in playlist["items"]:
            video_ids.append(item["snippet"]["resourceId"]["videoId"])

        return video_ids

    # TODO: Use this lol
    # POST https://developers.google.com/youtube/v3/docs/playlists/insert
    # def create_playlist(self, title: Optional[str] = "Discord", description: Optional[str] = "Generated using Discord To Playlist", visibility: Optional[str] = "unlisted") -> Resource:
    #     if visibility not in ["public", "unlisted", "private"]:
    #         raise RequestError(f"{Fore.RED}{Style.BRIGHT}[D2P] Invalid 'visibility' value input. Accepted inputs: ['public', 'unlisted', 'private']")
    #     else:        
    #         return self._authenticate_service().playlists().insert(
    #             part="snippet,status",
    #             body={
    #                 "snippet": {
    #                     "title": title,
    #                     "description": description
    #                 },
    #                 "status": {
    #                     "privacyStatus": visibility
    #                 }
    #             }
    #         ).execute()

    # POST https://developers.google.com/youtube/v3/docs/playlistItems/insert
    def update_playlist(self, playlist_id: str, video_ids: List[str]) -> None:
        for index, video_id in enumerate(video_ids):
            percentage = "{:.2f}%".format((index + 1) / len(video_ids) * 100)

            if video_id in self._get_playlist_content(playlist_id):
                print(f"{Fore.YELLOW}{Style.BRIGHT}[D2P]{Style.RESET_ALL} {percentage} Skipping {Fore.GREEN}{video_id}{Style.RESET_ALL} Video already in playlist")
                continue
            else:
                try:
                    self._authenticate_service().playlistItems().insert(
                        part="snippet",
                        body={
                            "snippet": {
                                "playlistId": playlist_id,
                                "resourceId": {
                                    "kind": "youtube#video",
                                    "videoId": video_id
                                }
                            }
                        }
                    ).execute()
                except HttpError as e:
                    if e.resp.status == 404:
                        print(f"{Fore.RED}{Style.BRIGHT}[D2P]{Style.RESET_ALL} {percentage} Skipping {Fore.GREEN}{video_id}{Style.RESET_ALL} Video not found")
                        continue
                    elif e.resp.status == 403:
                        raise RequestError(f"{Fore.RED}{Style.BRIGHT}[D2P] YouTube API quota exceeded. Try again in a few hours. For more info: https://developers.google.com/youtube/v3/determine_quota_cost")
                    else:
                        raise RequestError(f"{Fore.RED}{Style.BRIGHT}[D2P] Unpexpected YouTube API error. Error status code: {e.resp.status}")
                else:
                    print(f"{Fore.BLUE}{Style.BRIGHT}[D2P]{Style.RESET_ALL} {percentage} Adding {Fore.GREEN}{video_id}{Style.RESET_ALL} to {Fore.GREEN}{playlist_id}")
                    sleep(1)

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("-t", "--token", type=str, required=True, default=None, help="User secret Discord token")
    parser.add_argument("-tt", "--token_type", type=str.lower, required=False, default="User", choices=["user", "bearer", "bot"], help="Token type. Defaults to 'User'")
    parser.add_argument("-cid", "--channel_id", type=int, required=True, default=None, help="Text channel ID")
    parser.add_argument("-sid", "--start_id", type=int, required=True, default=None, help="Start message ID. MUST be greater than end_id. (Note that the message parser goes upwards)")
    parser.add_argument("-eid", "--end_id", type=int, required=True, default=None, help="End message ID. MUST be less than start_id. (Note that the message parser goes upwards)")
    parser.add_argument("-ytc", "--youtube_credentials", type=str, required=False, default="credentials.json", help="YouTube APP .json credentials file. Defaults to 'credentials.json'")
    parser.add_argument("-pid", "--playlist_id", type=str, required=True, default=None, help="YouTube Playlist ID https://www.youtube.com/playlist?list=<this_is_your_playlist_id>")
    args = parser.parse_args()

    discord = Discord(args.token_type, args.token)
    youtube = YouTube(args.youtube_credentials)

    message_generator = discord.generate_messages(args.channel_id, args.start_id, args.end_id)
    message_parser = discord.parse_messages(message_generator)
    youtube.update_playlist(args.playlist_id, message_parser)