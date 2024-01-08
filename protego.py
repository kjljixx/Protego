import discord
import discord.ext.commands
import datetime
import time
import json
import math
import tiktoken
import copy
import random
from characterai import PyCAI

intents = discord.Intents.all()

protego = discord.Client(intents=intents)

commandTree = discord.app_commands.CommandTree(protego)
#kjljixx:707944936678490152
whitelistFromSayingIndiaBan = [783862235982200842, 953009997648900167]

soorajLevelPerms = [1012527162647130142, 707944936678490152, 767442031311847464]

previousMessages = {} #track messages sent in the past 30 seconds
previousTimeouts = {}
spamDetectionStrictness = {}
spamPenalty = {}
webhooks = {}
webhooksInfo = {}

client = None
chat = None
tgt = None
lastConversationTime = 0

def updateDataFile():
  f = open("protegoData.json", "w")
  json.dump({"previousTimeouts":previousTimeouts, "spamDetectionStrictness":spamDetectionStrictness, "spamPenalty":spamPenalty, "webhooks":webhooksInfo}, f)
  f.close()

@commandTree.command(name="spamdetectionstrictness", description="Lower number is more strict. type:float,default:1000,max_value:100000,min_value:0")
async def commandSpamDetectionStrictness(interaction : discord.Interaction, strictness : float):
  if(strictness > 100000):
    strictness = 100000
  if(strictness < 0):
    strictness = 0

  if(not interaction.permissions.moderate_members):
    await interaction.response.send_message(content='You must have the "Timeout Members" permission in this server')
    return

  spamDetectionStrictness[str(interaction.guild.id)] = strictness
  updateDataFile()

  await interaction.response.send_message(content="Successfully set spam detection strictness for **"+interaction.guild.name+"** to **"+str(strictness)+"**")

@commandTree.command(name="spampenalty", description="How long (seconds) to timeout spammers for. type:float,default:60,max_value:100000,min_value:0")
async def commandSpamDetectionStrictness(interaction : discord.Interaction, penalty : float):
  if(penalty > 100000):
    penalty = 100000
  if(penalty < 0):
    penalty = 0

  if(not interaction.permissions.moderate_members):
    await interaction.response.send_message(content='You must have the "Timeout Members" permission in this server')
    return

  spamPenalty[str(interaction.guild.id)] = penalty
  updateDataFile()

  await interaction.response.send_message(content="Successfully set spam penalty for **"+interaction.guild.name+"** to **"+str(penalty)+"** seconds")

def indiaInText(text : str, level : int):
  if level==0:
    return (text.lower().count("i") >= 2 and text.lower().count("n") >= 1 and text.lower().count("d") >= 1 and text.lower().count("a") >= 1) or ("🇮🇳" in text.lower())
  if level==1:
    return ("india" in text.lower()) or ("🇮🇳" in text.lower())
  if level==2:
    return ("india" in text.lower()) or ("🇮🇳" in text.lower()) or ("sourpaj" in text.lower())
  return False

async def isReplyToWebhook(message : discord.Message, webhookID : int):
  if(not message.reference):
    return False
  channel = message.reference.resolved.channel
  messageID = message.reference.message_id
  originalMessage = await channel.fetch_message(messageID)
  if(webhookID==originalMessage.webhook_id):
    return True
  return False

def ukInText(text : str):
  return ("uk" in text.lower()) or ("🇬🇧" in text.lower()) or ("united kingdom" in text.lower())

def deIndianifyText(text : str):
  newText = text.lower()
  newText = newText.replace("india", "uk")
  newText = newText.replace("🇮🇳", "🇬🇧")
  newText = newText.replace("n", "u")
  newText = newText.replace("a", "k")
  newText = newText.replace("i", "")
  newText = newText.replace("d", "")

  return newText

protegoId = 1175197240130797658

encoding = tiktoken.get_encoding("cl100k_base")

def calculateSpamScore(serverId : str, userId : str):
  now = datetime.datetime.now(datetime.timezone.utc)
  spamScore = 0

  encodings = []
  for message in previousMessages[serverId][userId]:
    encodings.extend(encoding.encode(message.content))
    spamScore += (len(message.content)+100*(message.content.count("\n")+1))*(0.95**((now - message.created_at).total_seconds()))

  uniqueTokens = []
  for i in range(len(encodings)):
    if(not encodings[i] in uniqueTokens):
      uniqueTokens.append(encodings[i])

  if(uniqueTokens == 0):
    messageSimilarityMultiplier = 1
  else:
    messageSimilarityMultiplier = 2-2*float(len(uniqueTokens))/len(encodings)

  return spamScore*min(max(messageSimilarityMultiplier, 0.8), 2)

def removeOldMessagesFromPreviousMessages(serverId : str, userId : str, timeInSeconds : int):
  now = datetime.datetime.now(datetime.timezone.utc)
  for message in previousMessages[serverId][userId]:
    if (now - message.created_at).total_seconds() > timeInSeconds:
      previousMessages[serverId][userId].remove(message)

@protego.event
async def on_ready():
  f = open("protegoData.json", "r")
  data = json.load(f)
  for prevTimeoutsGuild, prevTimeoutsUsers in data["previousTimeouts"].items():
    previousTimeouts[prevTimeoutsGuild] = prevTimeoutsUsers
  for spamDetectSrictGuild, spamDetectStrictValue in data["spamDetectionStrictness"].items():
    spamDetectionStrictness[spamDetectSrictGuild] = spamDetectStrictValue
  for spamPenaltyGuild, spamPenaltyValue in data["spamPenalty"].items():
    spamPenalty[spamPenaltyGuild] = spamPenaltyValue
  for webhookChannel, webhookInfo in data["webhooks"].items():
    try:
      webhooksInfo[webhookChannel] = [webhookInfo[0], webhookInfo[1]]
      webhooks[webhookChannel] = await discord.Webhook.partial(id=webhookInfo[0], token=webhookInfo[1], client=protego).fetch()
    except:
      pass
  print("Loaded Data")
  await commandTree.sync()
  print("Synced Commands")

  global client
  global chat
  global tgt

  tokenFile = open("cAItoken.txt", "r")
  token = tokenFile.readline()

  client = PyCAI(token)
  
  chat = client.chat.get_chat("phRPCdYi0SyXm5f8m5MNdNFUgqCOKQIKbd8F_ycWYwE")

  participants = chat['participants']

  if not participants[0]['is_human']:
    tgt = participants[0]['user']['username']
  else:
    tgt = participants[1]['user']['username']

@protego.event
async def on_message(message : discord.Message):
  if message.webhook_id or message.author.bot or message.channel.category_id == 992514586249003050: #Texylvania #important category
    return
  if message.channel.id == 1016073290470674493: #Texylvania #spammers channel
    return
  
  if not str(message.guild.id) in previousMessages.keys():
    previousMessages[str(message.guild.id)] = {}

  if str(message.author.id) in previousMessages[str(message.guild.id)].keys():
    previousMessages[str(message.guild.id)][str(message.author.id)].append(message)
  else:
    previousMessages[str(message.guild.id)][str(message.author.id)] = [message]

  removeOldMessagesFromPreviousMessages(str(message.guild.id), str(message.author.id), 30)
  if len(previousMessages[str(message.guild.id)][str(message.author.id)])==0:
    del previousMessages[str(message.guild.id)][str(message.author.id)]

  spamScore = calculateSpamScore(str(message.guild.id), str(message.author.id))

  if(not str(message.guild.id) in spamDetectionStrictness.keys()):
    spamDetectionStrictness[str(message.guild.id)] = 1000
    updateDataFile()
  if(spamScore > spamDetectionStrictness[str(message.guild.id)]):
    print(message.author.name+" spamScore: "+str(spamScore))

    #Timeout user who spammed
    if not str(message.guild.id) in previousTimeouts.keys():
      previousTimeouts[str(message.guild.id)] = {}
    if(not str(message.author.id) in previousTimeouts[str(message.guild.id)].keys()):
      previousTimeouts[str(message.guild.id)][str(message.author.id)] = 0
    updateDataFile()
    
    if(not str(message.guild.id) in spamPenalty.keys()):
      spamPenalty[str(message.guild.id)] = 60
      updateDataFile()
    await message.author.timeout(datetime.timedelta(seconds=(spamPenalty[str(message.guild.id)])))

    previousTimeouts[str(message.guild.id)][str(message.author.id)] += 1
    updateDataFile()

    #Delete all spam messages
    numMessagesDeleted = 0
    for message in previousMessages[str(message.guild.id)][str(message.author.id)]:
      try:
        await message.delete()
        numMessagesDeleted += 1 #numMessagesDeleted is only incremented if message still exists
      except:
        continue
    del previousMessages[str(message.guild.id)][str(message.author.id)]

    #Send an info message to that the user has been timouted
    await message.channel.send("Timeouted <@"+str(message.author.id)+"> for **"+str(spamPenalty[str(message.guild.id)])+"** seconds for spamming. **"+str(numMessagesDeleted)+"** spam message(s) deleted. <@"+str(message.author.id)+"> has been timeouted for spamming **"+str(previousTimeouts[str(message.guild.id)][str(message.author.id)])+"** time(s) in this server so far, including this time.")

    return
  global lastConversationTime
  if (indiaInText(message.content, 2) or (str(message.channel.id) in webhooks.keys() and await isReplyToWebhook(message, webhooksInfo[str(message.channel.id)][0])) or (time.time() <= lastConversationTime+30 and random.randint(1, 3)==1)) and (message.guild.id == 992514255570087977 or message.guild.id == 786683761684250686):
    global client
    global chat
    global tgt
    # if(time.time() > lastConversationTime + 3600):
    #   chat = client.chat.new_chat("phRPCdYi0SyXm5f8m5MNdNFUgqCOKQIKbd8F_ycWYwE")
    lastConversationTime = time.time()

    newContent = deIndianifyText(message.content)

    inputText = message.author.display_name+" says:"
    if(message.reference):
      channel = message.reference.resolved.channel
      messageID = message.reference.message_id
      originalMessage = await channel.fetch_message(messageID)
      inputText += '(Replying to or mentioning the message by '+originalMessage.author.display_name+':"'+originalMessage.content+'")'
    inputText += message.content
    inputText += "\n*System: Your, Sourpaj's, personality is to love india, hate the uk, and be super dry*."
    data = client.chat.send_message(
      chat['external_id'], tgt, inputText
    )
    newContent = "<@"+str(message.author.id)+"> "+data['replies'][0]['text']
    
    if(not str(message.channel.id) in webhooks.keys()):
      mimicWebhook = await message.channel.create_webhook(name="mimic")
      webhooks[str(message.channel.id)] = mimicWebhook
      webhooksInfo[str(message.channel.id)] = [mimicWebhook.id, mimicWebhook.token]
      updateDataFile()
    else:
      mimicWebhook = webhooks[str(message.channel.id)]

    await mimicWebhook.send(content=newContent, username="Sourpaj", avatar_url="https://characterai.io/i/80/static/avatars/uploaded/2024/1/6/V4gvi-Mda4iz5Fvcw_-4Bt6fzk3PIRGC6cX2BBS-bek.webp")

    return
  if (indiaInText(message.content, 1)) and (not message.author.id in whitelistFromSayingIndiaBan) and (message.guild.id == 992514255570087977):
    newContent = deIndianifyText(message.content)

    mimicWebhook = await message.channel.create_webhook(name="mimic")
    await mimicWebhook.send(content=newContent, username=message.author.display_name, avatar_url=message.author.display_avatar.url)
    await mimicWebhook.delete()

    await message.delete()

    return
  if ukInText(message.content) and message.guild.id == 992514255570087977:
    await message.add_reaction("❤️")

    return

tokenFile = open("discordtoken.txt", "r")
token = tokenFile.readline()

protego.run(token)