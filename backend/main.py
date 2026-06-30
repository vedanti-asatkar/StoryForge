from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI 
from dotenv import load_dotenv
import os
from langchain_core.tools import tool
import random
from langchain_groq import ChatGroq
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import CharacterTextSplitter

load_dotenv()

app=FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

llm=ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"),
    model_name="llama-3.3-70b-versatile",
    model_kwargs={"tool_choice": "auto"}
)
@tool
def roll_dice(sides:  int=20)->int:
    """Roll a dice with given number of sides. Use this when player attempts an action that requires luck or skill, such as persuading, sneaking, attacking."""
    return random.randint(1, sides)

@tool
def update_hp(amount: int)->str:
    """"Update the player's HP. Use negative amount for damage, positive for healing.Example -10 for damage, +5 for healing"""
    game_state["hp"]+=amount
    return f"HP updated to {game_state['hp']}"

@tool
def add_to_inventory(item:str)->str:
    """Add an item to the player's inventory when they pick something up."""
    game_state["inventory"].append(item)
    return f"{item} Added to inventory"

tools=[roll_dice, update_hp, add_to_inventory]
llm_with_tools=llm.bind_tools(tools)

with open("lore/lore.txt", "r") as f:
    lore_text=f.read()

text_splitter=CharacterTextSplitter(chunk_size=200, chunk_overlap=20, seperator="\n")
lore_chunks=text_splitter.split_text(lore_text)

embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
vector_store = FAISS.from_texts(lore_chunks, embeddings)

conversation_history = [
    SystemMessage(content="""You are a dark and mysterious dungeon master. Stay in character always. Keep responses immersive but not too long.
IMPORTANT: You MUST use tools in these situations:
- ALWAYS call roll_dice when player attempts any action (attacking, sneaking, persuading)
- ALWAYS call update_hp with a negative amount when player takes damage
- ALWAYS call update_hp with a positive amount when player heals
- ALWAYS call add_to_inventory when player picks up an item
Never skip these tool calls. They are mandatory.""")
]

game_state = {
    "hp": 100,
    "inventory": [],
    "quest": "No active quest"
}

class CharacterSetup(BaseModel):
    name:str
    character_class:str
    genre:str

@app.post("/start")
def start_game(character: CharacterSetup):
    game_state["hp"]=100
    game_state["inventory"]=[]
    game_state["quest"]="No active quest"

    conversation_history.clear()
    conversation_history.append(SystemMessage(content=f"""You are dark and mysterious dungeon master running a {character.genre} RPG.
    The player's character is {character.name}, a {character.character_class}
    Stay in character always. Keep responses immersive bit not too long.
    IMPORTANT: You must use tools in these situations:
    - ALWAYS call roll_dice when player attempts any action
    - ALWAYS call update_hp with negative amount for damage, positive for healing
    -ALWAYS call add_to_inventory when player picks up an item
    -When you need to roll dice, call the roll_dice function directly. Do not describe calling it in text."""))

    opening = llm_with_tools.invoke(conversation_history + [HumanMessage(content=f"Begin the adventure for {character.name} the {character.character_class}.")])
    conversation_history.append(opening)
    
    return {"response": opening.content, "game_state": game_state}

class PlayerMessage(BaseModel):
    message: str

@app.post("/chat")
def chat(player_input: PlayerMessage):
    from langchain_core.messages import ToolMessage

    conversation_history.append(HumanMessage(content=player_input.message))
    try:
        relevant_lore = vector_store.similarity_search(player_input.message, k=2)
        lore_context = "\n".join([doc.page_content for doc in relevant_lore])
        response = llm_with_tools.invoke(conversation_history)
        conversation_history.append(response)

        if response.tool_calls:
            for tool_call in response.tool_calls:
                if tool_call["name"] == "roll_dice":
                    result = roll_dice.invoke(tool_call["args"])
                elif tool_call["name"] == "update_hp":
                    result = update_hp.invoke(tool_call["args"])
                elif tool_call["name"] == "add_to_inventory":
                    result = add_to_inventory.invoke(tool_call["args"])
                conversation_history.append(ToolMessage(content=str(result), tool_call_id=tool_call["id"]))

            final_response = llm_with_tools.invoke(conversation_history)
            conversation_history.append(final_response)
            return {"response": final_response.content, "game_state": game_state}

        return {"response": response.content, "game_state": game_state}
    
    except Exception as e:
        # if tool call fails, retry without tools
        simple_response = llm.invoke(conversation_history)
        conversation_history.append(simple_response)
        return {"response": simple_response.content, "game_state": game_state}