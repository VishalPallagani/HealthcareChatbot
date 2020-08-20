from parlai.core.agents import create_agent_from_model_file
from sentence_transformers import util
import csv
from random import random, choice


# Select the question part of the bot input
def extract_question(input):
    # Split before the ?
    partition = input.partition('?')
    input = partition[0] + partition[1]
    # Split before . if there's one
    input = input.partition('.')
    # While there is multiple sentece, we delete them
    while '.' in input[1]:
        input = input[2]
        input = input.partition('.')
    input = input[0]
    # Change to get a question ask by the user
    input = input.replace('your ', 'my ')
    input = input.replace('are you ', 'am I ')
    input = input.replace('you ', 'I ')
    return input


# Select the first sentence of the answer
def extract_answer(input):
    # Select the part before the .
    partition = input.partition('.')
    input = partition[0] + partition[1]
    # Select the part before the !
    partition = input.partition('!')
    input = partition[0] + partition[1]
    # Change to get an answer describing the user
    return input

def swap_time_answer(input):
    input = input.replace('my ', 'your ')
    input = input.replace('am I ', 'are you ')
    input = input.replace('I ', 'you ')
    return input


# Add the user input and the question if necessary
def analyse_store_answer(user_input, bot_input):
    # We store if the sentence start by I'm or I+something and if the bot was asking a question
    if '?' in bot_input and user_input[0] == 'I' and len(user_input) > 5 and (user_input[1:4] == "'m " or user_input[1] == ' '):
        # Extract the question in the bot input
        bot_input = extract_question(bot_input)
        answer = extract_answer(user_input)
        if not ("your " in answer or 'are you ' in answer or "you " in answer or "you?" in answer or "what about I ?" in
                bot_input or "how about I ?" in bot_input):
            answer = swap_time_answer(answer)
            # Save the question and the answer
            file_user_facts = open("data/user_facts.csv", 'a')
            writer = csv.writer(file_user_facts, delimiter=';')
            writer.writerow([bot_input.replace('\n', " "), answer])
            file_user_facts.close()


# Search for the max of a list and return it with the index
def max_index(list_value):
    index = 0
    maximum = 0
    i = 0
    for element in list_value:
        if element > maximum:
            maximum = element
            index = i
        i = i+1
    return maximum, index


def add_generic_question(bot_input, blender_bot):
    if '?' not in bot_input['text']:
        threshold = 0.8
        if random() > threshold:
            file = open("data/generic_questions.txt")
            question_add = choice(file.read().splitlines())
            bot_input.force_set('text', bot_input['text'] + question_add)
            blender_bot.self_observe({'text': question_add})
            file.close()
    return bot_input


# Answer to the user
def next_answer(blender_agent, user_input, boolean_finish=False):
    blender_agent.observe({'text': user_input, "episode_done": boolean_finish})
    # Extract the memory
    questions_embedding, answer = blender_agent.memory
    if questions_embedding is not None:
        # Convert the user_input to a tensor
        query_embedding = blender_agent.embedder.encode(user_input, convert_to_tensor=True)
        # Find the closest sentence in the facts compared to the user input
        cos_scores = util.pytorch_cos_sim(query_embedding, questions_embedding)[0]
        top_result, index = max_index(cos_scores)
    else:
        top_result = 0
    # If the user is asking a question close to the one in the stored question we respond with the appropriate answer
    if top_result > 0.75:
        response = blender_agent.act(answer[index], from_db=True)
    # Else we use the blender_agent answer
    else:
        response = blender_agent.act()
        response = add_generic_question(response, blender_agent)
    return response['text']


# Create the agent and return it
def create_agent_and_persona(persona=''):
    blender_agent = create_agent_from_model_file("zoo:blender/blender_90M/model")
    blender_agent.observe({'text': persona})
    return blender_agent
