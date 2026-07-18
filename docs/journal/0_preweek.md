# Preweek Technical Documentation

## Technical Goal
As someone working already in IT for some years with experience both in DEV and DEVOPS, the technical goal of Preweek (Explore) is to 
gather information about how each agent architectures behaves in practice. 

 While a coding harness and out of the box agents perform relatively well on coding and above average for devops tasks, the industry is fast 
 advancing towards the need of being capable of picking the correct architecture for building solutions, and recognizing the advantages and disadvantages of each.


[Ref 1] Examples of Agent Architectures
- An agent file with referenced files eg. AGENT.md,  @~/docs/*.MD
- Agent Skills driven by main agent eg. ~/.skills
- Filesystem Subagent driven by a coding harness or Coding Agent SDK eg. ~/subagents
- AI workflow automation platform eg. n8n
- Use a generic AI Agent SDK that leverages plug and plays generic AI packages.
- Use low level first-party LLM SDKs and write our own agentic loop
- Use REST APIs directly, write our own agentic loop
  - The agentic loop is model-driven orchestration  with middleware programmatic guidance
  - The agentic loop is code-driven orchestration


## Technical hypothesis
Based on our [Ref 1]
- An agent file with referenced files eg. AGENT.md,  @~/docs/*.MD   enough for "stateless" tasks (when generating artifacts with a 
well-defined structure, such as Terraform code), but not enough to interract with live systems. You run the risk of not enough (or too much) context, halucinations, or having the user act as a tester for the agent, constantly hand holding

- Agent Skills driven by main agent eg. ~/.skills  improves the previous architecture by giving extra context to an agent. However the 
context is static, and succeptible to be affected by outside systems.

- Filesystem Subagent driven by a coding harness or Coding Agent SDK eg. ~/subagents   - valid choice, but requires tasks that can be 
paralelized. For tasks requiring one solid agent, probably not that useful. 

- AI workflow automation platform eg. n8n - not evaluated yet

- Use a generic AI Agent SDK that leverages plug and plays generic AI packages. - potentiall being locked by changes in the interfaces. e.g 
OpenAI SDK will be more developed for OpenAi models than other provider models. 

- Use low level first-party LLM SDKs and write our own agentic loop - considerably more complex than previous solutions

- Use REST APIs directly, write our own agentic loop                - not evaluated yet



## Technical Observations
An Agent.md could connect to the MUD after multiple spams of shell commands. Due to the non deterministic nature of the AI (and do to my 
loss of game data at some point) i ran two times the agent, and interestingly the actions were different (one ran a .sh script and adjusted it, the other just spammed shell commands) but both were highly inneficient and nothing that you could run in a "production environment"

 Skills and Subagents preformed accompanied with a script to manage the telnet session. It's very important to note that the login 
improvement comes from the deterministic Telnet script, not necessarily from Skills or subagents, so i wouldn't be too quick to atribute the improvement to an architecture change They were able to play the MUD, providing an improvement over Agent.md on login side of things, but that's where the party ended. The agent was unable to adapt, kept asking clarification questions, was unfocused, produced less than stellar .md data files (which often forgot to update).
    
 The result of the run was a dramatic
    I've exhausted all viable options. The character is fundamentally trapped in an unnavigable sewer system. This session has reached its end. 
    Let me stop the game and document the lessons learned:


## Technical Conclusions

AGENT.md and Skills DO influence model behaviour, but they DO NOT by themselves provide a reliable runtime architecture.These mechanisms 
must be implemented outside the prompt layer.
    MUD is a stateful environment. Each action changes the world, and later decisions depend on accurately recording those changes.
Observing the state -> record observations -> adjust the state on given obsevations -> Select next action -> execut said action -> record 
the new state -> Detect loops, failures, or goal completion -> Repeat within an execution budget
Leaving this entire loop to the model results in inconsistent behaviour and unreliable state tracking as it can be seen in the chaos that world.md is

### Ideas for next weeks
- A Telnet session adapter.
- A parser that converts game responses into structured observations.
- A JSON state store for rooms, exits, inventory, status, and action history.
- A bounded set of domain-specific tools.
- A code-driven execution loop.
- A model call for selecting the next action.
- A verifier that confirms whether the expected state transition occurred.
- Loop detection and execution budgets.
- Explicit success and terminal-failure predicates.
- Trace logging for every observation, decision, action, and state change.

