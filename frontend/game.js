async function startGame(){
    const name= document.getElementById("player-name").value
    const characterClass=document.getElementById("character-class").value
    const genre=document.getElementById("genre").value
    
    const response = await fetch("http://127.0.0.1:8000/start", {
        method: "POST", 
        headers: {"Content-type": "application/json"}, 
        body:JSON.stringify({ name: name, character_class: characterClass, genre: genre })
    })
    const data = await response.json()  
    document.getElementById("character-screen").style.display = "none"
    document.getElementById("game-screen").style.display = "block"
    const cleanResponse = data.response.replace(/roll_dice\([^)]*\)/g, '🎲')
    document.getElementById("story-text").innerText = cleanResponse
    updateStats(data.game_state)
}
function updateStats(game_state){
    document.getElementById("hp").innerText = "HP: " + game_state.hp
    document.getElementById("inventory").innerText = "Inventory: " + game_state.inventory.join(", ")
}
async function sendMessage() {
    const message = document.getElementById("player-input").value

    const response = await fetch("http://127.0.0.1:8000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: message })
    })

    const data = await response.json()

    const cleanResponse = data.response.replace(/roll_dice\([^)]*\)/g, '🎲')
    document.getElementById("story-text").innerText += "\n\n" + cleanResponse
    document.getElementById("player-input").value = ""
    updateStats(data.game_state)
}