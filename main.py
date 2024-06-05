from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
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
    rank: str
    role1: str
    role2: str
    rank_value: Optional[int] = None  # Add this line to include rank_value

class TeamRequest(BaseModel):
    players: List[Player]
    roles: List[str]

@app.get("/")
def create_greeting():
    greeting = "FFG StackMaker"
    return greeting

@app.post("/create-teams")
def create_teams(request: TeamRequest):
    players = request.players
    roles = request.roles

    # Rank mapping
    rank_mapping = {
        'Iron4': 1, 'Iron3': 2, 'Iron2': 3, 'Iron1': 4,
        'Bronze4': 5, 'Bronze3': 6, 'Bronze2': 7, 'Bronze1': 8,
        'Silver4': 9, 'Silver3': 10, 'Silver2': 11, 'Silver1': 12,
        'Gold4': 13, 'Gold3': 14, 'Gold2': 15, 'Gold1': 16,
        'Platinum4': 17, 'Platinum3': 18, 'Platinum2': 19, 'Platinum1': 20,
        'Diamond4': 21, 'Diamond3': 22, 'Diamond2': 23, 'Diamond1': 24,
        'Master': 25, 'Grandmaster': 26, 'Challenger': 27
    }

    # Convert ranks to numerical values for sorting
    for player in players:
        player.rank_value = rank_mapping.get(player.rank, 0)

    # Sort players by rank
    players.sort(key=lambda x: x.rank_value, reverse=True)

    # Initialize team lists
    team1 = {role: None for role in roles}
    team2 = {role: None for role in roles}

    def assign_roles(team, players, roles):
        unassigned_players = []
        for role in roles:
            for player in players:
                if (team[role] is None and
                    (player.role1 == role or player.role2 == role) and
                    player not in team.values()):
                    team[role] = player
                    break
            if team[role] is None:
                for player in players:
                    if player not in team.values():
                        team[role] = player
                        break
        return [player for player in players if player not in team.values()]

    unassigned_players = assign_roles(team1, players, roles)
    assign_roles(team2, unassigned_players, roles)

    # Convert teams to list for response with assigned roles
    def create_team_list(team):
        team_list = []
        for role, player in team.items():
            if player:
                team_list.append({
                    "name": player.name,
                    "rank": player.rank,
                    "assigned_role": role
                })
        return team_list

    team1_list = create_team_list(team1)
    team2_list = create_team_list(team2)

    return {"team1": team1_list, "team2": team2_list}
