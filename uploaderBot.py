import asyncio, json, os, re, natsort
from pyrogram import Client, filters, errors
from pyrogram.errors import FloodWait

async def uploadToChannel(coursesDirectory='readyToUpload'):
    if not os.path.exists("terabitSecAthena.session"):
        api_id=input("API_ID: ")
        api_hash=input("API_HASH: ")
        uploaderBot = Client("uploaderBot", api_id=api_id,api_hash=api_hash)
    else:
        uploaderBot= Client("uploaderBot")
    output = []
    async with uploaderBot:
        courses = os.listdir(coursesDirectory)

        for course in courses:
            courseInfoFile = open(f"{coursesDirectory}/{course}/courseInfo.json")
            courseInfo = json.loads(courseInfoFile.read())
            courseInfoFile.close()
            # setting courses properties
            
            courseName = re.sub('_', ' ', course)  # generating converted course name
            courseName = re.sub('-', ' ', courseName)

            courseSize = courseInfo['size']  # in bytes
            courseTime = 0

            channelId = await uploaderBot.create_channel(courseName)
            channelId = channelId.id
            coursePath = f"{coursesDirectory}/{course}"
            
            blocksInfo = open(f"{coursesDirectory}/{course}/blocksInfo.json", 'r')
            blocks = json.load(blocksInfo)["blocks"]
            blocksInfo.close()

            blockFiles = os.listdir(f"{coursesDirectory}/{course}/blocks")
            blockFiles = natsort.natsorted(blockFiles)

            for block in blockFiles:  # upload blocks video
                blockNumber = int(block[:-4])
                block = blocks[blockNumber - 1]

                blockPath = f"{coursePath}/blocks/{blockNumber}.mp4"
                moduleName = block[-2][0]
                moduleName = moduleName.split('/')[2:-1]
                moduleName = '/'.join(moduleName)

                message = ''

                videoNameAndTimestamp = [item for item in block]
                videoNameAndTimestamp = videoNameAndTimestamp[1:-1]
                for videoName, timestamp in videoNameAndTimestamp:
                    videoName = videoName.split('/')[-1]
                    videoName = videoName.split('.')[:-1]
                    videoName = '.'.join(videoName)

                    message += f"{timestamp} {videoName}\n"

                blockSecs = block[-1]
                courseTime += blockSecs

                videoId = await uploaderBot.send_video(
                    channelId, blockPath,
                    width=1280, height=720, duration=blockSecs,
                    thumb="assets/thumb.jpeg",
                    progress=lambda current, total: print(f'[+] Uploading block #{blockNumber}: {((current * 100) // total)}%\r', end=''),
                )
                videoId = videoId.id

                header = f"__#Bloco{blockNumber:03d}__\n\n"
                header += f"**{moduleName}**\n"
                bottom = f"\n\n@terabitSec 🦜"
                finalMessage = header + message + bottom

                try:
                    pass
                    await uploaderBot.send_message(channelId, finalMessage, reply_to_message_id=videoId)
                except FloodWait as error:
                    await asyncio.sleep(error.x)
                    await uploaderBot.send_message(channelId, finalMessage, reply_to_message_id=videoId)

                print()
            print()

            if f"terabitSec-materials" in os.listdir(f"{coursesDirectory}/{course}"):  # upload course materials
                materials = os.listdir(f"{coursesDirectory}/{course}/terabitSec-materials")
                materials = sorted(materials)
                for f in materials:
                    materialIndex = f.split('.')[-1]
                    await uploaderBot.send_document(
                        channelId, f"{coursesDirectory}/{course}/terabitSec-materials/{f}",
                        caption=f"__#materiais__",
                        progress=lambda current, total: print(f'[+] Uploading material {f}: {((current * 100) // total)}%\r', end=''),
                        )
                    print(f"[+] Uploaded material: {coursesDirectory}/{course}/terabitSec-materials/{f}")

            # course index
            message = "⚠️ Atenção ⚠️\n\n"
            message += "Clique aqui para ver o Menu de navegação.\n"
            message += "Utilize as # para navegar rapidamente entre os blocos de vídeos.\n"
            message += "Para acessar os materiais, utilize o #materiais\n\n"

            blockNumber = 1
            modulesAndBlocks = {}

            for block in blocks:
                moduleName = block[-2][0]
                moduleName = moduleName.split('/')[2:-1]
                moduleName = '/'.join(moduleName)

                if moduleName not in modulesAndBlocks:
                    modulesAndBlocks[moduleName] = [blockNumber]
                else:
                    modulesAndBlocks[moduleName].append(blockNumber)
                blockNumber += 1

            for module in modulesAndBlocks:
                message += "\n" + module + "\n"
                for block in modulesAndBlocks[module]:
                    message += f"#Bloco{block:03d}; "
                message = message[:-2]  # cutting final "; "
                message += "\n"


            message += "\n\ngreetings from \n@terabitSec 🦜"
            isFirstIndex = True
            try:
                if len(message) <= 4096:
                    info = await uploaderBot.send_message(channelId, message)
                    await info.pin()
                else:
                    finalMessage = ""
                    message = message.splitlines()
                    for line in message:
                        line += '\n'
                        if len(line) + len(finalMessage) > 4096:
                            info = await uploaderBot.send_message(channelId, finalMessage)
                            if isFirstIndex:
                                await info.pin()
                                isFirstIndex = False

                            finalMessage = line
                        else:
                            finalMessage += line

                    if finalMessage:
                        info = await uploaderBot.send_message(channelId, finalMessage)
                        if isFirstIndex:
                            await info.pin()
                            isFirstIndex = False

            except FloodWait as err:
                await asyncio.sleep(error.x)
                info = await uploaderBot.send_message(channelId, finalMessage)
                if isFirstIndex:
                    await info.pin()
                    isFirstIndex = False

            # set channel description
            invite = await uploaderBot.export_chat_invite_link(channelId)

            hour = round(courseTime // 3600)
            minute = round((courseTime % 3600) // 60)
            seconds = round(courseTime % 60)
            prettyCourseTime = f"{hour:02d} hora(s) e {minute:02d} minuto(s)"

            description =  f"{courseName}\n"
            description += f"Tamanho: {courseSize / (1024 ** 3):.2f}GiB\n"
            description += f"Duração: {prettyCourseTime}\n"
            description += f"Convite: {invite}\n\n"
            description += f"@terabitSec"

            await uploaderBot.set_chat_description(channelId, description)

            output.append([courseName, courseSize, prettyCourseTime, invite])

    return output

if __name__ == "__main__":
    asyncio.run(uploadToChannel())
