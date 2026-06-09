"""Entry point + screen router (default framework: Streamlit).

Run:  streamlit run cli/app.py
The CLI imports ONLY backend.api — never data sources, models, or the DB directly.
"""
from __future__ import annotations
# import streamlit as st
# from backend import api
# from cli.screens import guest_home, auth, user_home, prediction, settings


def main() -> None:
    """
    Maintain a screen stack in session state for back-navigation.
    Guest -> (login/register) -> user_home -> {prediction, settings}.
    On any network error from the backend, show a friendly popup; never crash.
    TODO: implement routing.
    """
    raise NotImplementedError


if __name__ == "__main__":
    main()
