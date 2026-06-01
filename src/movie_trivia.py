"""Movie Trivia generator — reads from content bank, LLM fallback."""

import random
import bank_manager

HOOKS = [
    "You won't believe what happened behind the scenes:",
    "This movie secret was hidden for years:",
    "Most people don't know this about their favorite movie:",
    "This famous scene almost didn't make the cut:",
    "The real story behind this movie moment is incredible:",
    "Hollywood kept this secret quiet for decades:",
    "One small detail changed the entire movie:",
    "This movie fact sounds fake but it's 100% true:",
]

FALLBACKS = [
    ("Titanic's Jack Could Have Lived", "The famous door scene from Titanic — Jack dies while Rose survives on a wooden door. Director James Cameron confirmed that Jack could not fit on the door. But in 2022, a MythBusters-style experiment proved both could have fit. Cameron later said in an interview: 'Jack had to die. It's called art, not science.'"),
    ("Star Wars Sound Effects", "The iconic lightsaber hum was created by sound designer Ben Burtt. He recorded the hum of an old movie projector combined with the interference from a television set. The blaster sound came from striking a tight wire with a hammer. And Darth Vader's breathing was Burtt breathing through a scuba regulator."),
    ("Wizard of Oz Used Real Poison", "The Wicked Witch of the West's green makeup in The Wizard of Oz (1939) contained copper-based paint that was toxic. Actor Margaret Hamilton had to go through a strict detox process after filming. One stunt required her to disappear in a burst of fire — but the trapdoor malfunctioned, and she suffered second-degree burns."),
    ("Psycho's Toilet Scene Changed Movies", "Alfred Hitchcock's Psycho (1960) featured the first toilet flush ever shown on screen. The Hays Code had banned showing toilets in films, but Hitchcock fought for it. That single flush broke a Hollywood taboo that had lasted 30 years."),
    ("The Shining's Impossible Hotel Room", "In The Shining (1980), the layout of the Overlook Hotel is physically impossible. The exterior shot shows a 5-story building, but the interior sets were built on a soundstage with corridors that don't align. The famous 'no room 237' scene? The hotel map shows room 237 exists, but the corridor behind it is too short. Stanley Kubrick did this on purpose to create unease."),
    ("Jurassic Park's T-Rex Vision", "The famous line 'Don't move. T-Rex can't see you if you don't move' is scientifically wrong. Paleontologists confirmed that T-Rex had excellent vision, better than a hawk. Director Steven Spielberg knew this but kept it because it made the scene more tense. The real fact was later included in the film's DVD commentary."),
    ("Forrest Gump's History Edits", "Forrest Gump (1994) used CGI to place Tom Hanks into real historical footage. The scene where Gump shakes hands with JFK used body doubles and face replacement technology that was groundbreaking for its time. The technology was so advanced that it won the film its first Visual Effects Oscar."),
    ("The Matrix's Bullet Time", "The famous 'bullet time' effect in The Matrix (1999) was invented by filming 120 still cameras arranged in a circle around the actor. Each camera fired in sequence, creating the illusion of time freezing while the camera moves. The technique was so expensive that they only had one chance to get each shot right."),
    ("Jaws' Mechanical Shark", "The mechanical shark in Jaws (1975) kept breaking down. Its real name was 'Bruce.' Because Bruce failed constantly, director Steven Spielberg had to imply the shark's presence rather than show it. This 'flaw' is what made the film terrifying — you see less, you fear more."),
    ("E.T.'s Reese's Pieces Deal", "E.T. (1982) originally had E.T. eating M&M's. Mars Inc. turned down the product placement. Hershey's agreed to let Reese's Pieces be used instead. Within two weeks of the film's release, Reese's Pieces sales tripled. It's considered one of the most successful product placements in history."),
    ("Pulp Fiction's Chronological Order", "Pulp Fiction (1994) is famously told out of order. If you watch the scenes chronologically, Vincent Vega dies halfway through the story. Quentin Tarantino wrote the script this way specifically so that audiences would rewatch it. He said: 'The movie isn't confusing. You just have to watch it twice.'"),
    ("The Sixth Sense Twist Was Hidden", "The Sixth Sense (1999) has one of cinema's most famous twists: Bruce Willis was dead the whole time. Director M. Night Shyamalan hid clues throughout the film — Willis never interacts directly with anyone except the boy. When the film was released, theaters reported audiences rewatching immediately to spot the clues."),
    ("Indiana Jones and the Real Gun", "In Indiana Jones and the Raiders of the Lost Ark (1981), Indy shoots a swordsman instead of fighting him. Harrison Ford was sick with dysentery and couldn't film the complex fight scene. He suggested: 'Just shoot him.' Spielberg agreed, and the improvised moment became one of the film's most memorable scenes."),
    ("The Godfather's Real Cat", "The opening scene of The Godfather (1972) features Marlon Brando holding a cat. The cat was a stray that studio cat wranglers found on the lot. Brando insisted on keeping it during the scene. The cat's purring was so loud that dialogue had to be re-recorded in post-production."),
    ("Frozen's 'Let It Go' Was Almost Cut", "The song 'Let It Go' from Frozen (2013) was nearly removed from the film. Early test audiences found it 'too Broadway.' The songwriters, Kristen Anderson-Lopez and Robert Lopez, fought to keep it. It won the Oscar for Best Original Song, and the film became the highest-grossing animated film of all time at release."),
    ("Harry Potter's Real Owls", "The owls in the Harry Potter films were real, not CGI. Animal trainers used multiple owls for each scene because owls can only fly short distances in controlled conditions. Hedwig was played by several different male snowy owls — males are pure white while females have spots. The trainers had 48-hour shifts to keep the owls healthy under studio lights."),
    ("The Lion King's Hidden Subliminal Message", "The Lion King (1994) caused controversy when an animator admitted to spelling 'SEX' in a cloud of dust during the 'Circle of Life' scene. The letters S, E, and X are formed by floating dust particles. Disney later digitally removed it. The animator said it was a prank, not a subliminal message."),
    ("Back to the Future's Delorean", "The DeLorean time machine in Back to the Future (1985) was chosen because it looked 'alien-like.' Director Robert Zemeckis originally wanted a refrigerator, but decided a car was more cinematic. The DeLorean company had gone bankrupt before filming, so production bought remaining stock. Only about 9,000 DeLoreans were ever made."),
    ("The Dark Knight's Real Hospital", "The scene in The Dark Knight (2008) where the hospital explodes — Christopher Nolan used a real abandoned building and real explosives. The demolition company gave Nolan one chance. The explosion was delayed by a few seconds, which Heath Ledger's Joker improvised by tapping his detonator repeatedly. Nolan kept it in the final cut."),
    ("Avatar's Language Creation", "For Avatar (2009), James Cameron hired linguist Paul Frommer to create a fully functional Na'vi language. The language has over 2,000 words and its own grammar rules. Fans have since learned to speak it fluently. Cameron said: 'If you're going to build a world, you build it completely.'"),
]


def generate_movie_trivia_script() -> dict:
    entry = bank_manager.pick("movie_trivia")
    if entry:
        print(f"  Using banked movie trivia ({bank_manager.count('movie_trivia')} left)")
        return entry

    print("  Bank empty, generating fresh movie trivia...")
    return _try_llm() or _fallback()


def _fallback() -> dict:
    items = random.sample(FALLBACKS, min(2, len(FALLBACKS)))
    hook = random.choice(HOOKS)
    image_prompts = [
        f"cinematic movie poster style, {title}, dramatic lighting, film grain, 9:16 vertical, Hollywood golden hour, vintage movie set photography"
        for title, _ in items
    ]
    tts_lines = [f"{title}. {story}" for title, story in items]
    return {
        "title": f"{hook} {items[0][0]}",
        "hook": hook,
        "trivia_titles": [title for title, _ in items],
        "stories": [story for _, story in items],
        "image_prompts": image_prompts,
        "script": " ".join(tts_lines),
        "tts_script": " ".join(tts_lines),
    }


def _try_llm() -> dict | None:
    try:
        from src.script_generator import _generate
        prompt = (
            "Give me 2 true behind-the-scenes movie trivia facts with short explanations (8-12 words each). "
            "Each must be a verified real fact from a well-known movie. "
            "Format exactly:\n"
            "MOVIE: [movie title and the trivia headline]\n"
            "TRIVIA: [short explanation, 8-12 words]\n\n"
            "Make them fascinating, surprising, and 100% factual."
        )
        system = "You write verified true movie trivia facts. Every detail must be accurate and sourced from documented production history."
        raw = _generate(prompt, temperature=0.7, max_tokens=1000, system=system)
        if not raw:
            return None
        items = []
        current = {}
        for line in raw.split("\n"):
            line = line.strip()
            if line.upper().startswith("MOVIE:"):
                if current.get("movie") and current.get("trivia"):
                    items.append((current["movie"], current["trivia"]))
                current = {"movie": line.split(":", 1)[-1].strip()}
            elif line.upper().startswith("TRIVIA:") and current:
                current["trivia"] = line.split(":", 1)[-1].strip()
        if current.get("movie") and current.get("trivia"):
            items.append((current["movie"], current["trivia"]))
        if items and len(items) >= 2:
            hook = random.choice(HOOKS)
            image_prompts = [
                f"cinematic movie poster style, {movie}, dramatic lighting, film grain, 9:16 vertical, Hollywood golden hour, vintage movie set photography"
                for movie, _ in items
            ]
            tts_lines = [f"{movie}. {trivia}" for movie, trivia in items]
            return {
                "title": f"{hook} {items[0][0]}",
                "hook": hook,
                "trivia_titles": [movie for movie, _ in items],
                "stories": [trivia for _, trivia in items],
                "image_prompts": image_prompts,
                "script": " ".join(tts_lines),
                "tts_script": " ".join(tts_lines),
            }
    except Exception as e:
        print(f"  LLM error: {e}")
    return None
