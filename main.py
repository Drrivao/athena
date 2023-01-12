import asyncio, glob, shutil, json
import uploaderBot, organizeCourses
from time import sleep
from services import telegram
from pyrogram.types import *
from pyrogram import Client, filters, errors, types
import os

f = open("configFiles/config.json", 'r')
configJson = json.load(f)
f.close()

PRIVATE_GROUPS_ID = configJson["PRIVATE_GROUPS_ID"]

if not os.path.exists("terabitSecAthena.session"):
    api_id=input("API_ID: ")
    api_hash=input("API_HASH: ")
    bot_token=input("BOT TOKEN: ")
    bot = Client("terabitSecAthena", api_id=api_id,api_hash=api_hash,bot_token=bot_token)
else:
    bot= Client("terabitSecAthena")

# global variables
global courses
courses = {}
coursesTypes = {}

@bot.on_message(filters.command('uploadcourses') & filters.chat(PRIVATE_GROUPS_ID))
async def course(client, message):
    global courses
    courses[len(courses) + 1] = []
    coursesTypes[len(courses) + 1] = None
    await message.reply(f"Please, forward messages with courses in rar or zip format. Starting the {len(courses)} course in queue.")
    

@bot.on_message(filters.document & filters.chat(PRIVATE_GROUPS_ID))
async def files(client, message):
    global courses
    if len(courses) > 0:
        coursesTypes[len(courses)] = "telegram"
        courses = await telegram.append(courses, message)
    else:
        await message.reply("Sorry, if you want start to upload a course you have first send /uploadcourses.")


@bot.on_message(filters.command('finish' ) & filters.chat(PRIVATE_GROUPS_ID))
async def finish(client, message):
    if len(courses) > 0:
        totalSize = 0

        outputMessage = f"**{len(courses)} COURSES**"
        await message.reply(outputMessage)

        for index in courses:  # execute in all courses
            outputMessage = f"**COURSE NUMBER {index}**\n"
            outputMessage += f"**FILES {len(courses[index])}**\n\n"

            for f in courses[index]:  # get params for each file
                for params in f[:-1]:
                    totalSize += params['fileSize'] 
                    outputMessage += f"**File Name:** {params['fileName']}\n"

                    if f[-1]:
                        outputMessage += f"    **File Size:** {params['fileSize']}MiB\n"
                        outputMessage += f"    **File Password:** {f[-1]}\n\n"
                    else:
                        outputMessage += f"    **File Size:** {params['fileSize']}MiB\n\n"

            await message.reply(outputMessage)

        outputMessage = f"**TOTAL SIZE: {totalSize:.2f}MiB**\n\n"
        outputMessage += "Proceed with download?"

        await bot.send_message(
            message.chat.id, outputMessage,
            reply_to_message_id=message.message_id,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Yes.", callback_data="yesDownload")],
                [InlineKeyboardButton("❌ No.",
                callback_data="noDownload")]
            ]))
    else:
        await message.reply("Sorry, I don't have any course in my queue.")


@bot.on_message(filters.command('password') & filters.chat(PRIVATE_GROUPS_ID))
async def zipFilePassword(client, message):
    global courses
    command = message.command

    errorMessage =  "Incorrect usage of password command `/password` detected.\n"
    errorMessage += "Please, ensure you are using by the right way:\n\n"
    errorMessage += "```/password courseIndex password```\n"
    errorMessage += "```/password courseIndex:fileIndex password```"

    if len(command) == 3:
        courseIndex = command[1]
        password    = command[2]

        if courseIndex.isdigit():
            courseIndex = int(courseIndex)
            if courseIndex <= len(courses) and courseIndex > 0:
                for f in courses[courseIndex]:
                    f[-1] = password

        elif ":" in courseIndex:
            courseIndex = courseIndex.split(":")
            if len(courseIndex) == 2:
                courseIndex, fileIndex = courseIndex
                if courseIndex.isdigit() and fileIndex.isdigit():
                    courseIndex = int(courseIndex)
                    fileIndex = int(fileIndex)
                
                if courseIndex <= len(courses) and courseIndex > 0:
                    courseFiles = courses[courseIndex]
                    if fileIndex <= len(courseFiles) and fileIndex > 0:
                        courses[courseIndex][fileIndex-1][-1] = password
        else:
            await message.reply(errorMessage)
    else:
        await message.reply(errorMessage)


@bot.on_callback_query()
async def callback_queries(client, callback_query):
    message = callback_query.message
    chatId = message.chat.id
    if chatId in PRIVATE_GROUPS_ID:
        messageId = message.message_id

        if callback_query.data == "yesDownload":  # when user click on Yes download
            await client.edit_message_text(       # informing to user the download has started
                chat_id = chatId,
                message_id = messageId,
                text = "**DOWNLOAD STARTED**"
            )

            global courses
            await telegram.download(courses, bot, client, message, chatId, messageId)  # TODO: change later to works with mega and google drive

            await client.send_message(
                chatId, "🕐 **Download finished.**"
            )

            await asyncio.sleep(5)

            await client.send_message(
                chatId, "🕐 **Rendering courses.**"
            )
            organizeCourses.main()

            await bot.send_message(
                chatId, "✅ **Courses are ready.**",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Upload.", callback_data="yesUpload")],
                    [InlineKeyboardButton("❌ Do not upload.", callback_data="noUpload")]
                ]))

            courses = {}
        
        elif callback_query.data == "yesUpload":
            await client.edit_message_text(  # informing to user the download has started
                chat_id = chatId,
                message_id = messageId,
                text = "**UPLOAD STARTED**"
            )

            infos = await uploaderBot.uploadToChannel()

            # generating block messages cards
            for info in infos:  # generating courses message
                courseName, courseSize, courseTime, invite = info
                message =  f"**{courseName}**\n"
                message += f"💾| **Tamanho:** {courseSize / (1024 ** 3):.2f}GiB\n"
                message += f"🕒| **Duração:** {courseTime}\n"
                message += f"🌎| **Legendas**: foo\n\n"

                message += f"[⬇️ Assistir curso ⬇️]({invite})"

                await bot.send_photo(chatId, "assets/thumb.jpeg",
                    caption=message
                    )

            await client.send_message(
                chatId, "Delete dowloaded data?",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Delete.", callback_data="yesDelete")],
                    [InlineKeyboardButton("❌ Do not delete.", callback_data="noUpload")]
                ]))


        elif callback_query.data == "yesDelete":
            for course in glob.glob("readyToUpload/*"):
                shutil.rmtree(course)

            await client.edit_message_text(  # informing to user the data was deleted
                chat_id = chatId,
                message_id = messageId,
                text = "**✅ Data deleted.**"
            )


bot.run()
