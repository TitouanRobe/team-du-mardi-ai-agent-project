from google.adk.agents.llm_agent import Agent
# Un agent vide qui ne fait rien, juste pour que l'import fonctionne
hotel_agent = Agent(name="HotelAgent", model="gemini-2.5-flash", instruction="Bientôt disponible.")