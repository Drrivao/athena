import asyncio
from time import sleep
from pyrogram import errors


async def append(courses, message):
    courses[len(courses)].append([{
        "fileName": message.document.file_name,
        "fileSize": round(message.document.file_size / (1024 ** 2), 2),
        "message": message
    }, ''])

    return courses


async def download(courses, bot, client, message, chatId, messageId):
    for index in courses:  # downloading courses
        await message.reply(f"**DOWNLOADING COURSE {index}/{len(courses)}**")
        counter = 0
        lastFileNames = []
        message = await bot.send_message(chatId, "**DOWNLOADING FILE**")
        for f in courses[index]:
            param = f[0]
            password = f[1]
    
            currentFileName = param['message'].document.file_name
            counter += 1
            try:
                await client.edit_message_text(
                    chat_id = message.chat.id,
                    message_id = message.message_id,
                    text = f"**DOWNLOADING FILE {counter}/{len(courses[index])}**"
                )
            except errors.exceptions.bad_request_400.MessageNotModified:
                pass

            if currentFileName in lastFileNames:
                lastFileNames.append(currentFileName)
                currentFileName += f".{lastFileNames.count(currentFileName)}"    
            else:
                lastFileNames.append(currentFileName)

            await bot.download_media(
                param["message"],
                progress = lambda c, t: print(f"[+] download compressed file: {currentFileName} [{(c * 100 / t):.2f}%]\r", end=''),
                file_name = f"downloads/{index}/{currentFileName}"
            )

            if password:
                passwordFile = open(f"downloads/{index}/{currentFileName}.terabitSecPASSWORD", 'w')
                passwordFile.write(password)
                passwordFile.close()

            print()  # reset carriage return

