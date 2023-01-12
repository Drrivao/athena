import pathlib, shutil, os, requests, json, re, glob, unicodedata, subprocess
from natsort import natsorted
from time import sleep


def main():
    # ensure directories to be in the right order. e.g:
    # course1/module1/submodule1/lesson1.mp4
    # course2/module1/lesson1.mp4
    # course2/course2@terabitSec-Materials.zip.001

    pathlib.Path("readyToUpload/").mkdir(exist_ok=True)
    pathlib.Path("courses/").mkdir(exist_ok=True)

    unzip()

    directories = os.listdir("courses")
    currentPath = '/'.join(__file__.split('/')[:-1])

    for directory in directories:
        directory = "courses/" + directory
        subtitleFiles = []

        for f in os.listdir(directory):
            f = f"{directory}/{f}"
            print(f"f={f}\ndirectory={directory}")
            if len(f.split('/')) >= 3:
                
                if f.split('/')[2].lower().endswith((".mp4", ".ts", ".srt", ".vtt")):
                    pathlib.Path(f"{directory}/namelessModule").mkdir(parents=True, exist_ok=True)
                    shutil.move(f, f"{directory}/namelessModule")


        for dirPath, dirs, files \
        in os.walk(directory):
            # filtering "courses/" string and course providers
            providers = ['#P']
            originalDirPath = dirPath
            dirPath = dirPath.split('/')
            print(dirPath)
            if len(dirPath) >= 3:
                if dirPath[2] not in providers:
                    dirPath = dirPath[1:]
                    dirPath = '/'.join(dirPath)
                else:
                    dirPath = dirPath[3:]
                    dirPath = '/'.join(dirPath)
            else:
                dirPath = dirPath[1:]
                dirPath = '/'.join(dirPath)
            print(dirPath)
            courseName = dirPath.split('/')[0]

            if files:
                for filename in files:
                    if filename.lower().endswith(('.srt', '.vtt')):
                        print(f"[+] found a subtitle file: {filename}")
                        subtitleFiles.append(originalDirPath + '/' + filename)

                for filename in files:
                    filenameWithoutExtension = '.'.join(filename.split('.')[:-1])
                    filePath = dirPath + '/' + filename
                    originalFilePath = originalDirPath + '/' + filename
                    
                    # converting to ascii to avoid ordering errors
                    dirAscii = unicodedata.normalize('NFKD', dirPath).encode('ascii', 'ignore').decode('ascii')
                    filenameAscii = unicodedata.normalize('NFKD', filename).encode('ascii', 'ignore').decode('ascii')
                    courseName = unicodedata.normalize('NFKD', courseName).encode('ascii', 'ignore').decode('ascii')

                    if filename.lower().endswith(('.mp4', '.ts', '.webm', '.mkv')):
                        for subtitle in subtitleFiles:
                            if subtitle == (originalDirPath + '/' + filenameWithoutExtension + '.srt') \
                                or subtitle == (originalDirPath + '/' + filenameWithoutExtension + '.vtt'):
                                print(f"[+] generating subtitles: {filename}")
                                try:
                                    addSubtitles(originalFilePath, subtitle)
                                except json.decoder.JSONDecodeError:
                                    print("[+] error subtitling")

                        print(f"[+] moving lesson: {filename}")
                        pathlib.Path(f"readyToUpload/{dirAscii}").mkdir(parents=True, exist_ok=True)
                        shutil.move(originalFilePath, f"readyToUpload/{dirAscii}/{filenameAscii}")
                    elif not filename.lower().endswith(('.srt', '.vtt')):
                        print(f"[+] moving material: {filename}")
                        pathlib.Path(f"readyToUpload/{courseName}/terabitSec-materials/{dirAscii}").mkdir(parents=True, exist_ok=True)
                        shutil.move(originalFilePath, f"readyToUpload/{courseName}/terabitSec-materials/{dirAscii}/{filenameAscii}")

        if os.path.exists(f"{currentPath}/readyToUpload/{courseName}/terabitSec-materials"):
            subprocess.call(["/usr/bin/7z", "-y", "-v1900M", 'a', \
                f"{currentPath}/readyToUpload/{courseName}/terabitSec-materials/{courseName.replace(' ', '_')}@terabitSec-materials.zip", \
                f"{currentPath}/readyToUpload/{courseName}/terabitSec-materials/"])

            materials = glob.glob(f"readyToUpload/{courseName}/terabitSec-materials/*")
            for material in materials:
                if not material.startswith(f"readyToUpload/{courseName}/terabitSec-materials/{courseName.replace(' ', '_')}@terabitSec-materials.zip"):
                    if os.path.isfile(material):
                        os.remove(material)
                    else:
                        shutil.rmtree(material)

    # generating course blocks
    readyCourses = os.listdir("readyToUpload")

    for directory in readyCourses:
        directory = "readyToUpload" + '/' + directory

        courseTime  = 6
        blocksInfo = {"blocks": [[]]}
        blacklistItems = [f"{directory}/terabitSec-materials", f"{directory}/blocksInfo.json", \
                          f"{directory}/courseInfo.json", f"{directory}/blocks"]

        blockNumber = 0
        blockSecs = 6
        lastDirPath = ""

        for dirPath, dirs, files in natsorted(os.walk(directory)):
            files = natsorted(files)
            for f in files:
                filePath = dirPath + '/' + f
                if (dirPath not in blacklistItems) and (filePath not in blacklistItems):
                    videoTime = subprocess.check_output(["/usr/bin/ffprobe", "-i", f'{filePath}', "-show_entries", \
                                                         "format=duration", "-v", "quiet", "-hide_banner", "-of" , \
                                                         "default=noprint_wrappers=1:nokey=1"])
                    videoTime = videoTime.decode('utf-8')[:-2]
                    videoTime = round(float(videoTime))

                    currentBlockSecs = blockSecs
                    if lastDirPath == dirPath:
                        if blockSecs + videoTime <= 3600:
                            blocksInfo["blocks"][-1].append([filePath, generatePrettyTime(currentBlockSecs)])
                            blockSecs += videoTime
                        else:
                            if blockNumber == 0 and len(blocksInfo["blocks"][0]) == 0:
                                blockNumber = len(blocksInfo) + 1
                            elif blockNumber != 0:
                                blockNumber += 1
                            blocksInfo["blocks"][-1].append(blockSecs)
                            blockSecs = 6 + videoTime
                            blocksInfo["blocks"].append([[filePath, generatePrettyTime(6)]])
                    else:
                        if blockNumber == 0 and len(blocksInfo["blocks"][0]) == 0:
                            blockSecs = 6 + videoTime
                            blocksInfo["blocks"][0] = [[filePath, generatePrettyTime(currentBlockSecs)]]
                        else:
                            blocksInfo["blocks"][-1].append(blockSecs)
                            blockSecs = 6 + videoTime
                            blocksInfo["blocks"].append([[filePath, generatePrettyTime(6)]])
                        blockNumber += 1

                    lastDirPath = dirPath
    
        pathlib.Path(directory + "/blocks").mkdir(parents=True, exist_ok=True)
        blocksInfo["blocks"][-1].append(blockSecs)
        blockNumber = 0

        for block in blocksInfo["blocks"]:
            blockNumber += 1
            block.insert(0, ["assets/intro.mp4", "00:00:00"])
            videos = block[:-1]  # removing block secs
            videos = [video[0] for video in videos]
            times = [video[1] for video in videos]
            
            print(f"[+] generating block {blockNumber}/{len(blocksInfo['blocks'])}")

            # generating fffmpeg command
            ffmpegCommand = "/usr/bin/ffmpeg\n-y\n"
            ffmpegComplexFilter = "-filter_complex\n"
            
            for stream in videos:
                print(f"    [+] adding video: {stream}")
                ffmpegCommand += f"-i\n{currentPath}/{stream}\n"

            counter = 0
            for stream in videos:
                ffmpegComplexFilter += f"[{counter}:v]setdar=dar=16/9,scale=1920:1080,setsar=sar=1/1[v{counter}]; "
                counter += 1

            counter = 0
            for stream in videos:
                ffmpegComplexFilter += f"[v{counter}][{counter}:a] "
                counter += 1

            ffmpegComplexFilter += f"concat=n={len(videos)}:v=1:a=1 [vv] [aa]\n"

            ffmpegCommand += f"{ffmpegComplexFilter}"
            ffmpegCommand += f"-map\n[aa]\n-map\n[vv]\n-preset\nsuperfast\n{directory}/blocks/{blockNumber}.mp4"
            ffmpegCommand += f"\n-c:v\nlibx265\n-crf\n28\n-vsync\n2\n-safe\n0\n-loglevel\nquiet\n-stats"
            
            ffmpegCommand = ffmpegCommand.splitlines()

            print("[+] rendering block to file")
            subprocess.run(ffmpegCommand)
            print()

        # generating json info files
        courseInfo = generateCourseInfo(directory)

        courseInfoJsonFile = open(f"{directory}/courseInfo.json", 'w')
        json.dump(courseInfo, courseInfoJsonFile, indent=4)
        courseInfoJsonFile.close()
        
        blocksInfoJsonFile = open(f"{directory}/blocksInfo.json", 'w')
        json.dump(blocksInfo, blocksInfoJsonFile, indent=4)
        blocksInfoJsonFile.close()

        # removing downloaded data
        for f in os.listdir(directory):
            if f"{directory}/{f}" not in blacklistItems:
                try:
                    os.remove(f"{directory}/{f}")
                except IsADirectoryError:
                    shutil.rmtree(f"{directory}/{f}")

    for f in glob.glob("courses/*"):
        shutil.rmtree(f)

    for f in glob.glob("downloads/*"):
        pass
        shutil.rmtree(f)


def generatePrettyTime(secs):
    hour = int(secs // 3600)
    minute = int((secs % 3600) // 60)
    seconds = int(secs % 60)
    prettyTime = f"{hour:02d}:{minute:02d}:{seconds:02d}"

    return prettyTime


def addSubtitles(f, subtitle):
    subtitleFile = open(subtitle, 'r')
    subtitleLines = subtitleFile.readlines()
    subtitleFile.close()

    if subtitleLines[0] == "WEBVTT\n":
        subtitleLines = subtitleLines[1:]
    subtitleLines = [line for line in subtitleLines if line != '\n']

    subtitleText = ''.join(subtitleLines)

    # subtitle timestamp enumerate
    timestamps = re.findall("[0-9]{1,}:[0-9]{1,}:[0-9]{1,}[\.,][0-9]{1,} --> [0-9]{1,}:[0-9]{1,}:[0-9]{1,}[\.,][0-9]{1,}\n", subtitleText)
    subtitleText = re.sub("[0-9]{1,}\n*[0-9]{1,}:[0-9]{1,}:[0-9]{1,}[\.,][0-9]{1,} --> [0-9]{1,}:[0-9]{1,}:[0-9]{1,}[\.,][0-9]{1,}\n", '', subtitleText)
    subtitleText = subtitleText.splitlines()

    if len(subtitleText) != len(timestamps):
        a = len(subtitleText) - len(timestamps)
        subtitleText = subtitleText[a:]

    subtitleFile = open(subtitle, 'w')
    lastLength = 0
    subtitleTextToFile = ''
    newlineCharacter = '\n'
    for i in range(len(subtitleText)):
        subtitleTextToFile += f"{i + 1}\n"
        subtitleTextToFile += f"{timestamps[i]}"

        translated = translateRequests(subtitleText[i])
        print(' ' * currentLength, end='\r')
        print(f"        [+] Translated string: [{re.sub(newlineCharacter, '', translated)}]", end='\r')

        currentLength = len(f"        [+] Translated string: [{translated}]")
        subtitleTextToFile += f"{translated}\n\n"

    print()
    subtitleFile.write(subtitleTextToFile)
    subtitleFile.close()

    print("[+] applying subtitles")
    output = '.'.join(f.split('.')[:-1]) + '-TEMPFILE.' +  f.split('.')[-1]
    ffmpegExitCode = subprocess.run(["/usr/bin/ffmpeg", "-y", "-i", f, "-vf", f"subtitles={subtitle}", output, "-loglevel", "quiet"]).returncode

    if ffmpegExitCode == 0:
        shutil.move(output, f)
    else:
        print(subtitleTextToFile)
        print("[+] subtitle is not valid or video path is broken, aborting")


def translateRequests(text, lang='pt'):
    head = {"User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0"}

    res = requests.get(url="https://www.translate.com/machine-translation",headers=head)
    cook = res.cookies.get_dict()

    dt = {'text_to_translate':text,'source_lang':'en','translated_lang':lang,'use_cache_only':'false'}
    res = requests.post(url="https://www.translate.com/translator/translate_mt",headers=head,data=dt,cookies=cook)
    res = json.loads(res.text)

    return res["translated_text"]


def generateCourseInfo(coursePath):
    courseInfo = {}

    # get course size
    size = 0
    for dirPath, dirs, files in os.walk(f"{coursePath}/blocks"):
        if files:
            for f in files:
                size += os.path.getsize(f"{dirPath}/{f}")

    for dirPath, dirs, files in os.walk(f"{coursePath}/terabitSec-materials"):
        if files:
            for f in files:
                size += os.path.getsize(f"{dirPath}/{f}")

    courseInfo = {"size": size}

    return courseInfo


def unzip():
    files = glob.glob("downloads/*/*")
    for f in files:
        courseNumber = f.split('/')[1]
        pathlib.Path(f"courses/{courseNumber}").mkdir(exist_ok=True)

        if not f.endswith(".terabitSecPASSWORD"):
            if f"{f}.terabitSecPASSWORD" in files:
                passwordFile = open(f"{f}.terabitSecPASSWORD", 'r')
                password = passwordFile.read()
                passwordFile.close()

                subprocess.run(["/usr/bin/7z", 'x', "-y", f, f"-p{password}", f"-ocourses/{courseNumber}"])
            else:
                subprocess.run(["/usr/bin/7z", 'x', "-y", f, f"-ocourses/{courseNumber}"])


if __name__ == "__main__":
    main()
