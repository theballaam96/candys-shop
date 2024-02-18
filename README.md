# Candy's Shop
A repository containing all songs converted to the DK64 Soundfont
# Downloading Custom Music
To download custom music for DK64 Randomizer, you can visit this [Site](https://theballaam96.github.io/pack_builder). Pick out any music you want and once you finish click on File > Download Candy Pack, or Download Binary Pack if you don't want Categorized Songs. If you want to update your pack in the future, just click on Upload Pack and The Pack Builder will select all songs in your pack
# Submissions
- There are a couple ways to submit your song. Both ways involve you making a Github account, Forking, and making a PR with your MP3 (If Applicable), MIDI, and Binary Files:
    - **Submission Form**:  The best and easiest way to submit your own converted music is to visit this [Site](https://theballaam96.github.io/submission_form) and follow the instructions. The last screen will give you a template that you just copy and edit paste into the Pull Request Comment. **DO NOT DELETE THE `IS SONG - DO NOT DELETE THIS LINE` LINE** 
    - **Directly from Github**: The second way is to directly create your Pull Request through Github. Only use this if you know your way around Github. You want to make a Pull request with the above files mentioned and edit this line here:
        ```
        IS SONG - DO NOT DELETE THIS LINE
        Game: <GAME NAME>
        Song: <SONG NAME>
        Category: <CATEGORY NAME: bgm | events | majoritems | minoritems>
        Composers: <COMPOSERS DELIMITED BY ,>
        Converters: <CONVERTERS DELIMITED BY ,>
        Audio: <URL TO YOUTUBE VIDEO>
        Tags: <LIST OF CATEGORIES DELIMITED BY ,>
        Additional Notes: <NOTES TO BE DISPLAYED ON PACK BUILDER SITE>
        Update Notes: <NOTES TO BE DISPLAYED IN MUSIC-FILES>
        ```
- If you delete the `IS SONG - DO NOT DELETE THIS LINE` Line, Github Actions will not recognize your PR as a song and will comment letting you know that your PR isnt a song. If this happens, just edit your comment and re-add that line on the top.
- After you submit your song, the Music Verifiers will review it and will either accept or decline it. If your submission is declined for any reason, one of the Music Verifiers will leave a comment in your pull request explaining the reason for the decline. You will know if your submission got accepted when we merge your Pull Request into the Main repository and it shows up in the #Music-Files Channel of Discord. It is highly recommended you keep your eye on your Pull Request as most of the time, that is the place where you'll be receiving your update
# Acceptable Song Submissions
- We will only accept songs converted from Video Game Music. There are some exceptions to Video Game Music that are not allowed:
   - **Licensed Video Game Music**: Some example include songs from the Guitar Hero franchise such as Through The Fire and Flames
   - **DMCA Prone Music**: DMCA Prone Intellectual Property Music such as Rick Astley's Never Gonna Give You Up or Michael Jackson's Moon Walker will **NOT** be added to the Pack Builder.
   - **Public Domain**: Any Music that is within the [Public Domain](https://en.wikipedia.org/wiki/Public_domain) **IS** Allowed to be submitted, as it's copyright has expired. If your song falls under this category, please ensure that your song is based on the original work that is in the public domain and [not any performances that are not in the public domain](https://www.youtube.com/watch?v=1Jwo5qc78QU&t=220s).
# Questions?
Visit the [Discord](https://discord.dk64randomizer.com) and ask any question in the #music-discussion channel. One of our many composers will help you with any questions you have!
