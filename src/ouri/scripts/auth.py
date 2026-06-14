"""One-time Oura OAuth authorization."""

from ouri.api.oauth import OAuthClient


def main() -> None:
    client = OAuthClient()
    client.run_interactive_flow()
    print("Done. Set OURI_DATA_SOURCE=live in .env to use your real Oura data.")


if __name__ == "__main__":
    main()
