from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Player(BaseModel):
    name: str
    rank: str
    role1: str
    role2: str
    rank_value: Optional[int] = None

class TeamRequest(BaseModel):
    players: List[Player]
    roles: List[str]

rank_mapping = {
    'Iron4': 1, 'Iron3': 2, 'Iron2': 3, 'Iron1': 4,
    'Bronze4': 5, 'Bronze3': 6, 'Bronze2': 7, 'Bronze1': 8,
    'Silver4': 9, 'Silver3': 10, 'Silver2': 11, 'Silver1': 12,
    'Gold4': 13, 'Gold3': 14, 'Gold2': 15, 'Gold1': 16,
    'Platinum4': 17, 'Platinum3': 18, 'Platinum2': 19, 'Platinum1': 20,
    'Diamond4': 21, 'Diamond3': 22, 'Diamond2': 23, 'Diamond1': 24,
    'Master': 25, 'Grandmaster': 26, 'Challenger': 27
}

def assign_roles(players, roles):
    # Sort players by rank descending
    players.sort(key=lambda x: x.rank_value, reverse=True)

    team1 = {role: None for role in roles}
    team2 = {role: None for role in roles}
    assigned_players = set()

    # Assign highest-ranked players to their main roles first
    for player in players:
        if player.name not in assigned_players:
            if not team1[player.role1]:
                team1[player.role1] = player
                assigned_players.add(player.name)
            elif not team2[player.role1]:
                team2[player.role1] = player
                assigned_players.add(player.name)

    # Assign remaining players to their secondary roles if their main role has been taken
    for player in players:
        if player.name not in assigned_players:
            if not team1[player.role2]:
                team1[player.role2] = player
                assigned_players.add(player.name)
            elif not team2[player.role2]:
                team2[player.role2] = player
                assigned_players.add(player.name)

    # Fill any remaining gaps with the best available players
    for player in players:
        if player.name not in assigned_players:
            for role in roles:
                if not team1[role]:
                    team1[role] = player
                    assigned_players.add(player.name)
                    break
                elif not team2[role]:
                    team2[role] = player
                    assigned_players.add(player.name)
                    break

    # Adjust teams to maximize the average rank of team1
    def calculate_average_rank(team):
        total_rank = sum(player.rank_value for player in team.values() if player)
        return total_rank / len(roles)

    team1_avg_rank = calculate_average_rank(team1)
    team2_avg_rank = calculate_average_rank(team2)

    if team1_avg_rank < team2_avg_rank:
        for role in roles:
            if team2[role] and team1[role]:
                if team2[role].rank_value > team1[role].rank_value:
                    team1[role], team2[role] = team2[role], team1[role]
                    break

    return team1, team2

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

@app.get("/")
def create_greeting():
    greeting = "FFG StackMaker"
    return greeting

@app.post("/create-teams")
def create_teams(request: TeamRequest):
    players = request.players
    roles = request.roles

    # Convert ranks to numerical values for sorting
    for player in players:
        player.rank_value = rank_mapping.get(player.rank, 0)

    team1, team2 = assign_roles(players, roles)

    if team1 is None or team2 is None:
        return {"error": "No optimal solution found."}

    team1_list = create_team_list(team1)
    team2_list = create_team_list(team2)

    return {"team1": team1_list, "team2": team2_list}

# Example usage
example_request = {
    "players": [
        {"name": "Reni", "rank": "Diamond4", "role1": "Adc", "role2": "Mid"},
        {"name": "Gjunti", "rank": "Diamond3", "role1": "Top", "role2": "Jungle"},
        {"name": "Aaron", "rank": "Diamond4", "role1": "Top", "role2": "Jungle"},
        {"name": "Sandy", "rank": "Master", "role1": "Mid", "role2": "Adc"},
        {"name": "Merlin", "rank": "Platinum1", "role1": "Mid", "role2": "Jungle"},
        {"name": "Chruune", "rank": "Diamond4", "role1": "Support", "role2": "Top"},
        {"name": "Mäc", "rank": "Bronze4", "role1": "Support", "role2": "Jungle"},
        {"name": "Albo", "rank": "Platinum4", "role1": "Adc", "role2": "Mid"},
        {"name": "Arno", "rank": "Silver3", "role1": "Support", "role2": "Adc"},
        {"name": "Joey", "rank": "Silver1", "role1": "Support", "role2": "Top"}
    ],
    "roles": ["Top", "Jungle", "Mid", "Adc", "Support"]
}

response = create_teams(TeamRequest(**example_request))
print(response)
