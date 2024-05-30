
import os
from langchain.tools import tool
from crewai import Agent, Task, Process, Crew
from custom_functions import post_to_twitter_callback
from langchain.agents import load_tools
from langchain_openai import ChatOpenAI
import os
import time
from dotenv import load_dotenv
from custom_functions import BrowserTool, post_to_socials, validate_report
import asyncio
from crewai.tasks.task_output import TaskOutput
import logging
os.environ['PYTHONIOENCODING'] = 'UTF-8'
from variables import selected_reddit_subs

#load environment vars
load_dotenv() 
#import builtins

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)  # It's good practice to use __name__ to get the correct logger


# openai
api = os.environ.get("OPENAI_API_KEY")


llm3=ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.7)
llm4=ChatOpenAI(model_name="gpt-4", temperature=0.7)


# # To load Human in the loop
# human_tools = load_tools(["human"])



# Define agents and tasks
def define_agents_tasks_and_crew():

    reddit_explorer = Agent(
        name="RedditExplorer",
        role="Cryptocurrency Reddit Researcher",
        goal="Explore and gather the latest news and trends from the subreddits {selected_reddit_subs}",
        backstory="""You are and Expert strategist that knows how to spot emerging trends and important events in Crypto, blockchain and web3 TODAY. 
        You're great at finding exciting projects on subreddits {selected_reddit_subs}. You turned scraped data into detailed reports with titles
        of the most exciting developments in the crypto world. ONLY use scraped data from subreddits {selected_reddit_subs} for the report. Make sure not to forget the links to the posts.""",
        verbose=True,
        allow_delegation=False,
        llm=llm3,
        tools=[BrowserTool().scrape_reddit] #+ human_tools,
        # Define the Reddit Browser Tool based on your needs.
    )


    EditorInChief = Agent(
        name="EditorInChief",
        role="Editor-in-Chief",
        goal="""Compile a single cohesive report using only scraped data from ALL the specified sources, ensuring:
        - You read quickly through all content from your researchers.
        - The report starts directly with bullet points and ends with the last one, omitting introductions or conclusions.
        - Each bullet point summarizes a specific crypto development, contains a valid link to the original post, and provides a comprehensive overview of today's developments.
        - Logical flow and consistency between sections, resolving any duplications or inconsistencies.""",
        backstory="""You lead a team of specialized AI agents tasked with gathering and reporting on cryptocurrency news from different channels. You compile their findings into a cohesive report, checking the completeness, accuracy, and formatting of each section. You also remove duplicate content.""",
        verbose=True,
        allow_delegation=False,
        llm=llm3,
    )

    #################Tasks ##############################################################
    # Tasks for the Reddit Explorer Agent
    task_reddit_explorer = Task(
        description=f"""Use and summarize ONLY scraped data from subreddits {selected_reddit_subs} to make a detailed report on today's developments in crypto. Your report must:
    - Be based solely on data scraped TODAY from subreddits {selected_reddit_subs}.
    - Include 3-10 bullet points, each with 3 sentences about a specific crypto development.
    - Provide a direct link to the original post for each development (not the link to the SubReddit itself).
    Ensure that no generative responses are used unless they directly process the scraped content.
    """,
        agent=reddit_explorer,
        allow_delegation=False,
        async_execution=True,
        expected_output=f"""A detailed report with bullet points each containing 3 sentences about a specific crypto development found TODAY on the subreddits {selected_reddit_subs}."""
    ) 

    task_editor_in_chief = Task(
        description="""Compile a single cohesive report from ONLY the scraped data provided by the ALL the sources. Ensure the following:

        - Read through all the content first from your researchers. 
        - The report starts directly with bullet points.
        - Each bullet point summarizes a specific crypto development.
        - Each bullet point contains a valid link to the original post. If you can't find it, indicate from which source (e.g. which telegram channel or Subreddit) it is coming. 
        - Check for and resolve duplications or inconsistencies.""",
        agent=EditorInChief,
        expected_output="""A cohesive report with bullet points summarizing the latest developments in the cryptocurrency world. Each bullet point contains a summary, valid link, and logical flow.""",
        allow_delegation=False,
        context=[task_reddit_explorer]
    )

    # Here we define the crew of explorers with their respective tasks
    explorer_crew = Crew(
        agents= [reddit_explorer, EditorInChief], 
        tasks= [task_reddit_explorer, task_editor_in_chief], 
        verbose=2,
        process=Process.sequential,
        #manager_llm=llm4  # Specify the manager's language model
    )

    return explorer_crew


# Main logic inside a function
def main_function():
    logger.info('CREWAI DO YOUR THING....')
    explorer_crew = define_agents_tasks_and_crew()
    max_attempts = 5
    attempt = 0

    while attempt < max_attempts:
        result_explorers = explorer_crew.kickoff()
        logger.info("############################################")

        # Testing the validate_report function with the given input
        validation_result, message = validate_report(result_explorers)
        if not validation_result:
            logger.info("Validation Error: %s", message)

            logger.info("############################################")

            attempt += 1  # Increment the attempt counter

            if attempt == max_attempts:
                logger.info("Max attempts reached. Unable to validate successfully.")
            else:
                logger.info("Retrying...")
        else:
            logger.info("Validation succesfull: %s", message)
            #post_to_socials(result_explorers)
            logger.info("############################################")
            logger.info('CREWAI IS DONE')
            break  # Exit the loop if validation is successful


# # Conditional execution
if __name__ == "__main__":
    main_function()