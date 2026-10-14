# 25. Voice and Realtime Agents

> As of October 2026. Tags: **(GA)** generally available · **(Preview)** beta/preview · **(⚠ verify)** not confirmed against primary sources.

## Where this fits

Voice assistants predate LLMs. Phone trees (IVR, "press 1 for billing"), Siri (2011) and Alexa (2014) ran a fixed pipeline: speech recognition, then an intent classifier with slot filling ("book_flight", city=Boston), then hand-written dialog rules, then speech synthesis. Every intent was hand-built, and anything off-script failed. In 2023, products put an LLM in the middle of that chain, a **cascade** of speech-to-text (STT) → LLM → text-to-speech (TTS). Conversation became open-ended, but slow. In May 2024, GPT-4o took audio in and produced audio out in one model, responding "in as little as 232 milliseconds, with an average of 320." OpenAI's Realtime API followed: beta Oct 1, 2024, GA Aug 28, 2025, with `gpt-realtime-2.1` current since Jul 2026, and the full-duplex GPT-Live 1 GA on Sep 10, 2026. Google offers the Gemini Live API. Claude's API takes text and images and returns text, so Claude fits voice as the middle stage of a cascade ([§07](07-multimodal.md)). [§24](24-computer-use-and-research-agents.md)'s agents could take seconds per step. A conversation can't.

## Why this exists

**Conversation is a real-time protocol.** Stivers et al. (2009) studied 10 languages and found the same pattern in all of them: speakers avoid overlapping and minimize silence between turns, and each language's average gap falls within 250 ms of the cross-language mean. Levinson and Torreira (2015) state the puzzle: gaps between turns are "of the order of 200 ms," but producing speech takes "over 600 ms." Listeners must therefore predict the end of your turn and plan their reply while you are still talking.

A text chatbot that takes two seconds feels fine, because tokens stream onto the screen. Two seconds of silence on a call feels broken. Callers say "hello?", repeat themselves, talk over the reply, or hang up.

**The mechanism makes this hard.** Every stage waits on the one before it. STT can't finalize until the user stops. The LLM can't emit a first token until it has prefilled the whole context (P10), and it decodes one token at a time (P1). TTS can't speak words that don't exist yet. Run these stages one after another and the delays add up to seconds. Voice engineering fits a chain of slow components into a human-sized gap, using the two tricks people use themselves: overlap the work (streaming) and predict the end of the turn.

## How it works (under the hood)

### The latency budget (P10)

The metric that matters is **voice-to-voice latency**: the time from the user's last syllable to the agent's first audible sound, measured at the user's ear. On the critical path of a cascade:

```text
user stops ─▶ turn detection ─▶ STT final ─▶ LLM first token ─▶ first clause ─▶ TTS first audio ─▶ network + playback ─▶ sound
              (a deliberate      (finalize    (prefill: prompt,   (decode until  (synthesize the    (RTT, jitter buffer,
               silence wait)      transcript)  history, tools)     speakable)     first phrase)      phone network)
```

Two things stand out:

- **The biggest item is often a deliberate wait.** In OpenAI's example config, the server waits 500 ms of silence before deciding you are done.
- **Latency is a distribution, not a number.** Budget the p95 (the latency 95% of turns beat), because callers remember the worst pauses, and p95s don't add up stage by stage.

The calculator below samples each stage from a long-tailed distribution and compares designs. Every number in it is a placeholder for your own measurements.

```python
import math, random

# Critical path after the user stops talking: (median_ms, p95_ms) per stage.
# PLACEHOLDER numbers for illustration, not vendor claims. Replace with your own measurements.
CASCADE = {
    "turn detection (silence wait)": (500, 700),
    "STT final transcript":          (100, 250),
    "LLM time to first token":       (350, 900),   # prefill grows with history + tools (P10)
    "LLM decode to first clause":    (120, 250),   # ~6-8 tokens before a speakable phrase
    "TTS time to first audio":       (120, 250),
    "network + jitter buffer":       (80, 200),
}
BUDGET_MS = 800                    # your product target; human turn gaps are ~200 ms

def draw(median, p95):             # lognormal: latency has a long right tail
    return random.lognormvariate(math.log(median), math.log(p95 / median) / 1.645)

def report(label, stages, n=20_000):
    random.seed(7)
    totals = sorted(sum(draw(m, p) for m, p in stages.values()) for _ in range(n))
    ok = sum(t <= BUDGET_MS for t in totals) / n
    print(f"{label:30} p50 {totals[n // 2]:5.0f} ms  p95 {totals[int(n * .95)]:5.0f} ms  "
          f"within {BUDGET_MS} ms: {ok:4.0%}")

report("cascade, everything streamed", CASCADE)
report("+ semantic turn detection", {**CASCADE, "turn detection (silence wait)": (250, 600)})
report("cascade, no LLM streaming", {**CASCADE, "LLM decode to first clause": (2500, 4000)})
report("speech-to-speech", {"turn detection (silence wait)": (250, 600),
                            "S2S time to first audio": (400, 900),  # one model, audio in/out
                            "network + jitter buffer": (80, 200)})
print("sum of the stage p95s:", sum(p for _, p in CASCADE.values()), "ms (p95s don't add up)")
```

With these placeholders, the streamed cascade lands near 1.35 s at the median. Smarter turn detection saves about 230 ms. Waiting for the full LLM reply pushes the median to about 3.8 s. One speech-to-speech model comes in around 0.8 s. The sum of the stage p95s (2.55 s) overstates the real p95 (about 1.95 s). Swap in measured numbers, and the calculator tells you which stage to attack first.

### Cascaded vs speech-to-speech

**Cascaded** (STT → text LLM → TTS):

- **Control.** The transcript is ordinary text, so you can log it, redact it, run policy checks on it, and test the reply before anything is spoken.
- **Any model.** You can use the strongest text model with the most mature tool calling, Claude included, and swap vendors stage by stage.
- **The cost:** latency adds up across handoffs, and **prosody** (tone, emphasis, hesitation, laughter) is lost. A transcript is a lossy compression: "fine." and "fine?!" become the same string. STT mistakes on names and numbers also propagate downstream.

**Speech-to-speech (S2S)**: audio tokens in, audio tokens out ([§07](07-multimodal.md)):

- **Speed and expressiveness.** One model means no handoffs, it hears tone, it replies with matching emotion, and the session handles barge-in.
- **The cost:** the transcript becomes a side channel rather than the source of truth, so auditing and testing get harder. You are limited to the vendor's preset voices. OpenAI notes that its cheaper mini realtime models trade away "instruction following and function calling."
- **Token billing.** OpenAI's Realtime API bills user audio at 1 token per 100 ms and assistant audio at 1 token per 50 ms, and the whole conversation is sent for each response.

**Full duplex plus a delegated backend** is the 2026 hybrid. OpenAI's GPT-Live "can listen and speak at the same time." A voice-native front model handles the conversation and delegates reasoning and tool use to a backend: either an OpenAI model, or "any model, agent harness, or service your application runs." It is billed at $0.05 per minute of voice, plus the backend. This is a fast talker paired with a slow thinker, and it lets you keep an existing text agent behind a voice front end.

### Streaming everything

Every stage consumes partial input and emits partial output:

- STT streams partial transcripts.
- The LLM streams tokens (`client.messages.stream(...)` on the Messages API).
- A chunker cuts text at clause boundaries.
- TTS synthesizes each phrase as it arrives.
- Playback starts on the first audio chunk.

Streaming turns a *sum of stage durations* into a *sum of first-chunk latencies*. The stub below wires the stages together with `asyncio` queues, the in-process equivalent of topics between streaming jobs.

```python
import asyncio, time
T0 = time.perf_counter()
def log(stage, msg): print(f"{(time.perf_counter() - T0) * 1000:5.0f} ms  {stage:<4} {msg}")
async def stt(mic, out):                  # streaming STT: consumes audio frames as they arrive
    words = []
    while (frame := await mic.get()) is not None:   # None = turn detection says "done"
        words.append(frame)               # (partial transcripts would be emitted here)
    await asyncio.sleep(0.10)             # finalize the transcript
    log("STT", "final: " + " ".join(words)); await out.put(" ".join(words))

async def llm(inp, out):                  # live: client.messages.stream(...) text deltas
    await inp.get()
    await asyncio.sleep(0.35)             # time to first token = prefill of the context (P10)
    for tok in "Sure. Your order shipped Tuesday, and it should arrive Friday.".split():
        await out.put(tok); await asyncio.sleep(0.02)          # ~50 tokens/s decode
    log("LLM", "last token"); await out.put(None)

async def chunker(inp, out):              # release text at clause boundaries, not at the end
    buf = []
    while (tok := await inp.get()) is not None:
        buf.append(tok)
        if tok[-1] in ".,?!":
            await out.put(" ".join(buf)); buf = []
    if buf: await out.put(" ".join(buf))
    await out.put(None)

async def tts(inp, first_audio):          # streaming TTS: speak each phrase as soon as it lands
    while (phrase := await inp.get()) is not None:
        await asyncio.sleep(0.12)         # time to first audio for this phrase
        first_audio.setdefault("t", time.perf_counter())
        log("TTS", f"speaking {phrase!r}")

async def main():
    mic, text, toks, phrases = (asyncio.Queue() for _ in range(4))
    for frame in ["where", "is", "my", "order", None]: mic.put_nowait(frame)  # user just finished
    first = {}
    await asyncio.gather(stt(mic, text), llm(text, toks), chunker(toks, phrases), tts(phrases, first))
    log("done", f"first audio at {(first['t'] - T0) * 1000:.0f} ms, before the LLM's last token")

asyncio.run(main())
```

"Sure." is audible at about 575 ms, before the LLM's last token at about 655 ms. Without streaming, first audio would wait for the whole reply plus its synthesis, and for a 150-token answer at 50 tokens per second that is seconds later. Two more tricks shave time:

- **Speculation.** Start the LLM on a stable partial transcript before turn detection fires, and discard the result if the user keeps talking. This spends tokens to buy time (P10).
- **Prompt caching** on the fixed system prompt and tools, which cuts prefill and therefore time to first token.

### Voice activity detection and turn detection

**Voice activity detection (VAD)** is a small classifier that labels short audio frames as speech or non-speech. **Turn detection** asks a harder, semantic question: is the user *done*? OpenAI's Realtime API offers two modes:

- **`server_vad`** decides by silence. You tune `threshold`, `prefix_padding_ms` and `silence_duration_ms`, and it emits `input_audio_buffer.speech_started` and `speech_stopped` events.
- **`semantic_vad`** uses "a semantic classifier to detect when the user has finished speaking, based on the words they have uttered." A trailing-off phrase gets a longer timeout than a definitive statement, and `eagerness` (low, medium, high, auto) tunes how quickly it commits.

Fixed silence has a built-in dilemma. Set it short and the agent cuts people off mid-thought. Set it long and every turn feels sluggish. LiveKit's turn detector shows why words alone aren't enough. A user who says "I need to think about that for a moment" and then pauses still has more to say. LiveKit's detector is an audio model that combines meaning with "intonation, pitch, and rhythm." This is the machine version of what Levinson and Torreira describe in humans: predict the end of the turn rather than wait for silence.

### Barge-in and interruptions

**Barge-in** means the user starts talking while the agent is speaking. Handling it correctly takes four steps:

```text
on speech_started while the agent is speaking:
    stop playback now; flush client, network and telephony audio buffers
    cancel in-flight LLM and TTS work (and decide whether running tools finish or cancel)
    truncate the assistant turn to the audio the user actually heard
    let turn detection classify it: real interruption → new turn; "mm-hm" or a cough → resume
```

The truncation step is the subtle one. The model is stateless (P2): if the history says the agent finished a sentence that the user never heard, the model believes something false about the conversation. With WebRTC and SIP connections, OpenAI's server "knows how much audio has been played" and truncates automatically. Over WebSocket, the client must send `conversation.item.truncate` with `audio_end_ms`. Even then, the transcript can't be precisely aligned to the audio. Two traps to plan for:

- **Echo.** Without echo cancellation, the agent hears its own voice and interrupts itself.
- **False barge-in.** Backchannels ("right," "mm-hm"), coughs and a television in the room aren't interruptions. Stopping for them is one of the most irritating voice bugs.

### Transports: WebRTC, WebSocket, SIP

- **WebSocket** is a persistent two-way connection over TCP, so delivery is reliable and in order. That suits server-to-server links, but on a lossy network one lost packet stalls everything queued behind it. For live audio, a late packet is worthless anyway. The client also owns playback and truncation. The Gemini Live API is a "stateful WebSocket connection," taking 16 kHz PCM in and returning 24 kHz.
- **WebRTC** is the browser and mobile standard for real-time media, carried over UDP. It comes with jitter buffers, packet-loss concealment and echo cancellation, and it drops late packets instead of waiting for them. OpenAI's browser flow has your server mint a short-lived client secret (`POST /v1/realtime/client_secrets`) so that your API key never reaches the browser.
- **SIP** (Session Initiation Protocol) is the signaling protocol of internet telephony. A SIP trunking provider turns a phone number into IP traffic. With OpenAI, you point the trunk at `sip:$PROJECT_ID@sip.api.openai.com;transport=tls`. A `realtime.call.incoming` webhook fires, and your backend accepts it with `POST /v1/realtime/calls/{call_id}/accept` plus the session config (model, voice, tools, instructions). Endpoints for reject, refer (transfer) and hangup cover the rest, and a sideband WebSocket lets your server watch events and run tools. GPT-Live's SIP path requires TLS signaling and encrypted (SRTP) audio.

The alternative to direct SIP is a **server audio bridge**: your application relays the call audio itself and owns both connections.

### Tool calling and the filler-speech problem

A 1.5-second CRM lookup is invisible in text chat and 1.5 seconds of dead air on a call. The options:

- **Filler speech.** Say "Let me pull up your order" before or during the tool call, either as the model's preamble or as a phrase the harness triggers when a tool starts.
- **Fewer slow calls.** Prefetch likely context when the call connects (caller ID → account), cache results, and run independent calls in parallel.
- **Delegation.** Keep talking while a backend works. In GPT-Live, "users can keep talking while backend work runs," and your application decides whether interrupted work finishes or is cancelled.

Filler has failure modes of its own. It can claim success early ("I've booked that") before the tool returns. It can repeat until it sounds robotic. It can promise something the tool then fails to deliver. OpenAI's guide says to measure "acknowledgments such as 'I'm checking' separately from the answer the caller needs" and to "verify that spoken confirmations match completed actions."

For consequential actions, read the details back and get a spoken yes: "a $500 transfer to the account ending 42, shall I go ahead?" The harness, not the model, then executes (P6). Alphanumerics are where STT errs most, so spell them back or accept keypad input. The Realtime API delivers keypad (DTMF) presses as events.

### State and context in long calls

Every response resends the conversation (P2), and audio is token-dense. At OpenAI's rates, a 20-minute call with 10 minutes of speech from each side accumulates about 6,000 user plus 12,000 assistant audio tokens, all resent on every turn, so total cost grows roughly with the square of the call length, as in [§11](11-agents.md). The controls:

- **Caching.** It applies automatically while the history stays unchanged, and editing earlier items "busts" it.
- **Truncation.** When the context overflows, the server drops the oldest items. A `retention_ratio` below 1.0 drops extra items so that truncation doesn't run, and invalidate the cache, on every turn.
- **Summaries.** Replace old turns with a summary (`conversation.item.delete`, then `conversation.item.create`).

Keep the facts that must survive in structured state your application owns, injected each turn ([§16](16-context-engineering.md), [§17](17-memory.md)): who the caller is, whether they are verified, their intent, and what has been done so far. Persist that state so a dropped call can resume ([§20](20-agent-runtime.md)).

### Evaluating voice agents

Score two layers separately.

- **Task:** were the tool arguments right, did the booking land in the system of record, and did the spoken confirmation match it?
- **Conversation:** p50 and p95 voice-to-voice latency, unwanted silence, overlap, yielding to interruptions, and recognition across accents, noise, names and numbers.

OpenAI's guide stages the work as **crawl** (synthetic speech, single turns, fixed audio for repeatable comparisons), **walk** (replayed human recordings, with real voices, microphones and rooms), and **run** (an independent simulated caller over multi-turn conversations, with interruptions and changing requirements). Change one factor at a time, and keep the caller, model configuration and transport fixed. Distinguish a broken eval run, such as a dropped connection, from a valid run in which the agent failed. Add human listening for naturalness and pacing ([§26](26-evals.md)).

### Telephony realities

The phone network is narrowband. G.711 μ-law or A-law audio is sampled at 8 kHz and carries roughly 300–3,400 Hz. Models are trained on 16–24 kHz audio, and the high frequencies that separate "s" from "f" are simply gone, so recognition gets worse. Every transcoding step loses a little more. OpenAI's Realtime API accepts `audio/pcmu`, and GPT-Live takes raw 8 kHz G.711 over WebSocket, so you can forward phone audio without converting it.

Then add the real world: speakerphones, cars, crosstalk, hold music, packet loss on mobile, voicemail greetings on outbound calls, and transfers to humans (SIP REFER). Build test sets from real call audio, not studio recordings.

### Safety: impersonation and consent

- **Voice cloning.** Generating speech "based on a short input clip" enables fraud through impersonation (GPT-4o system card). OpenAI's mitigation is to allow only preset voices, with a streaming output classifier that blocks audio not matching the chosen voice. It also observed "rare instances" of a model unintentionally imitating the *user's* voice.
- **Authentication.** Don't use a voice match, or caller ID, as an authentication factor. Both can be faked. OpenAI says to treat SIP headers as "untrusted caller metadata, not authorization." Verify identity out of band.
- **Disclosure.** Tell callers they are talking to an AI. The EU AI Act's Article 50(1) requires systems that interact with people to inform them, from Aug 2, 2026 ([§34](34-governance-regulation.md)). In the US, the FCC ruled in Feb 2024 that AI-generated voices count as "artificial" under robocall law, which brings consent requirements for such calls. Recording-consent rules vary by jurisdiction.
- **Injection by voice.** Anything a caller says is untrusted input (P9). Scope tools to the verified caller, and put read-back confirmation on consequential actions ([§32](32-security-guardrails.md)).

## Comparison

| Architecture | How it works | Strength | Weakness | When to choose |
|---|---|---|---|---|
| Cascaded (STT → LLM → TTS) | Three streamed stages joined by text | Inspectable transcript, any LLM, mature tools, swappable parts | Handoff latency adds up; loses tone; STT errors propagate | Regulated or tool-heavy agents; Claude-based voice |
| Speech-to-speech | One model, audio tokens in and out | Lowest latency, hears and conveys tone, built-in barge-in | Harder to audit and test; preset voices; vendor lock-in | Conversational products where feel matters |
| Full duplex + delegated backend | Voice model talks; backend reasons and calls tools | Talks while work runs; reuse an existing text agent | Two systems to keep consistent; newest pattern | Long tool calls; existing agent behind a voice front end |

| Transport | Layer | Strength | Weakness | Typical use |
|---|---|---|---|---|
| WebSocket | TCP, reliable and ordered | Simple, server-friendly | Head-of-line stalls on loss; client owns playback and truncation | Server-to-server, audio bridges |
| WebRTC | UDP media, jitter buffer, echo cancellation | Built for live audio; server tracks playback | More moving parts (ICE, codecs) | Browser and mobile clients |
| SIP (+ RTP/SRTP) | Telephony signaling plus media | Real phone numbers, transfers, DTMF | 8 kHz narrowband; carrier quirks | Inbound and outbound phone agents |

| Turn detection | Decides "done" by | Strength | Weakness |
|---|---|---|---|
| Fixed silence (`server_vad`) | N ms of silence | Simple, predictable | Too short interrupts; too long feels slow |
| Semantic (`semantic_vad`, text models) | Probability the words are complete | Waits on trailing phrases, fast on definite ones | Fooled by mid-turn pauses |
| Audio turn model | Words plus intonation, pitch, rhythm | Closest to human prediction | Another model to run and tune |
| Push-to-talk | The user presses a button | No ambiguity | Not natural; only fits some products |

## What it didn't solve

Coding, computer-use, research and voice agents are each impressive in demos, and none of them is useful unless you can measure whether it works. Each makes measurement harder in its own way. GUIs have no verifier, research reports have no single right answer, and voice adds timing and audio quality on top of task success. All of it is sampled, so every number is a distribution (P4). → Next: [§26 Evals](26-evals.md)

## Check your understanding

**Q: Why is a two-second delay acceptable in text chat but not on a voice call?**

Human conversation runs on gaps of about 200 ms, with listeners predicting the end of each turn. Silence on a call is ambiguous: has the agent failed, or the line dropped? In text chat, streamed tokens show progress, so the same delay feels fine. Voice therefore needs streaming at every stage and smart turn detection, and you should budget the p95, not only the median.

**Q: What would happen if you set the silence threshold to 150 ms to cut latency?**

The agent would answer faster on clean, definite turns, but it would treat ordinary pauses (breathing, "um," thinking) as the end of the turn. It would cut users off mid-sentence and answer half-questions, which forces repairs that cost far more time than the 350 ms saved. Use semantic or audio-based turn detection to be quick on definite endings and patient on trailing ones.

**Q: Cascaded or speech-to-speech for a bank's phone agent that calls account tools and must keep auditable records?**

Usually cascaded, or full duplex with a text backend. The transcript is the system of record, so you can log it, redact it and check policy before the agent speaks. You can also use the strongest tool-calling model and test text outputs with ordinary evals. You pay in latency and lost tone, so stream every stage and fix turn detection. Choose speech-to-speech when conversational feel matters more than auditability.

**Q: Why must you truncate the assistant's turn after a barge-in, and what goes wrong if you don't?**

The model only knows what the history says (P2). If the history records a full sentence the user never heard, the model reasons from a false shared state. It may say "as I mentioned," skip a question that never reached the user, or contradict itself. Truncate to the audio actually played: WebRTC and SIP sessions on OpenAI do this server-side, and over WebSocket the client sends `conversation.item.truncate`.

**Q: Why does streaming change voice latency from a sum of stage durations into a sum of first-chunk latencies?**

Without streaming, each stage waits for the previous stage's complete output, so you pay full STT plus full generation plus full synthesis. With streaming, TTS starts on the first clause while the LLM is still decoding, so only each stage's *first* output sits on the critical path. The tradeoff is engineering complexity: chunking, cancellation, and keeping text and audio aligned on interruption.

**Q: Why do voice agents need filler speech during tool calls, and what is the risk?**

A tool call's latency becomes dead air, which callers read as failure. A short acknowledgment covers the gap. The risk is that filler claims or implies results the tool hasn't produced ("I've booked it"), or repeats until it sounds robotic. Keep fillers non-committal, measure them separately from the real answer, and confirm only after the harness has the result.

**Q: Why is a caller's voice or caller ID not an acceptable authentication factor?**

A few seconds of audio can clone a voice, and caller ID and SIP headers can be spoofed. OpenAI's docs call SIP headers "untrusted caller metadata, not authorization." Authenticating on either hands an impersonator your tools. Verify identity out of band (a one-time code, an app confirmation), and scope tools to the verified identity (P9).

## Takeaways

- The constraint is human: turn gaps of about 200 ms. Measure voice-to-voice latency at the user's ear, at p50 and p95 (P10).
- A cascade gives you control and any LLM, Claude included. Speech-to-speech gives speed and tone. Full duplex with a delegated backend splits the talker from the thinker.
- Stream every stage. That turns a sum of durations into a sum of first-chunk latencies.
- Turn detection is a prediction problem. Fixed silence is a crude baseline; semantic and audio models do better.
- Barge-in means stop, flush, cancel and truncate the history to what was actually heard (P2).
- Pick the transport for the client: WebRTC for browsers, WebSocket for servers, SIP for phones, where the audio is 8 kHz and noisy.
- Cover tool latency with honest filler or delegation, confirm consequential actions aloud, and never authenticate by voice or caller ID (P6, P9).

## Sources

- Stivers et al., "Universals and cultural variation in turn-taking in conversation," PNAS (2009): https://pubmed.ncbi.nlm.nih.gov/19553212/
- Levinson & Torreira, "Timing in turn-taking and its implications for processing models of language," Frontiers in Psychology (2015): https://pubmed.ncbi.nlm.nih.gov/26124727/
- OpenAI, "GPT-4o System Card" (Oct 2024): https://arxiv.org/abs/2410.21276
- OpenAI, Voice agents guide (architectures, evaluation, latency): https://developers.openai.com/api/docs/guides/voice-agents
- OpenAI, Getting started with the Realtime API: https://developers.openai.com/api/docs/guides/realtime
- OpenAI, Voice activity detection: https://developers.openai.com/api/docs/guides/realtime-vad
- OpenAI, Realtime conversations (interruption and truncation): https://developers.openai.com/api/docs/guides/realtime-conversations
- OpenAI, Telephony and SIP: https://developers.openai.com/api/docs/guides/realtime-sip
- OpenAI, Voice latency and cost (audio tokens, caching, truncation): https://developers.openai.com/api/docs/guides/voice-latency-cost
- OpenAI, Getting started with GPT-Live: https://developers.openai.com/api/docs/guides/live
- OpenAI, API changelog (Realtime beta Oct 1, 2024; GA Aug 28, 2025; gpt-realtime-2.1 Jul 6, 2026; GPT-Live 1 Sep 10, 2026): https://developers.openai.com/api/docs/changelog
- Google, Gemini Live API: https://ai.google.dev/gemini-api/docs/live
- LiveKit, Turn detector docs: https://docs.livekit.io/agents/build/turns/turn-detector/
- Pipecat (open-source voice agent framework): https://github.com/pipecat-ai/pipecat
- Anthropic, Streaming Messages: https://platform.claude.com/docs/en/build-with-claude/streaming
- EU AI Act, Article 50 (transparency obligations): https://artificialintelligenceact.eu/article/50/
- FCC, Declaratory Ruling FCC 24-17 on AI-generated voices under the TCPA (adopted Feb 2, released Feb 8, 2024): https://docs.fcc.gov/public/attachments/FCC-24-17A1.pdf
- FCC, "FCC Makes AI-Generated Voices in Robocalls Illegal" (news release, Feb 8, 2024): https://docs.fcc.gov/public/attachments/DOC-400393A1.pdf
