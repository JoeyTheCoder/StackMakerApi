from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

class Player(BaseModel):
    name: str
    rank: int
    role1: str
    role2: str

class TeamRequest(BaseModel):
    players: List[Player]
    roles: List[str]

@app.get("/")
def create_greeting():
    greeting = "FFG StackMaker"
    return greeting

@app.post("/create-teams")
def create_teams(request: TeamRequest):
    # Implement the team creation logic here
    # For now, let's just split the players into two teams randomly

    players = request.players
    team1 = players[:len(players)//2]
    team2 = players[len(players)//2:]

    return {"team1": team1, "team2": team2}
