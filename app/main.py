import os
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Form, Depends, HTTPException, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import selectinload
from app.models import Base, User, Poll, Question, Option, Vote
from app.auth import hash_password, verify_password, create_session, read_session
from app.renderer import render

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://voting:voting@db:5432/voting")
engine = create_async_engine(DATABASE_URL, pool_size=10, max_overflow=20, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(title="Voting App", lifespan=lifespan)

async def load_user(db: AsyncSession, session_token: str | None) -> User | None:
    if not session_token: return None
    uid = read_session(session_token)
    if not uid: return None
    res = await db.execute(select(User).where(User.id == uid))
    return res.scalar_one_or_none()

def nav_html(user: User | None) -> str:
    if user:
        return f'<span class="user">👤 {user.username}</span><a href="/polls/new">+ Создать</a><a href="/logout">Выйти</a>'
    return '<a href="/login">Вход</a><a href="/register">Регистрация</a>'

def page(*, title: str, content: str, user: User | None, status_code: int = 200) -> HTMLResponse:
    return HTMLResponse(render("base.html", title=title, nav=nav_html(user), content=content), status_code=status_code)

def error_block(message: str) -> str:
    return f'<div class="error">{message}</div>' if message else ""

def action_icons(edit_link: str, delete_button: str) -> str:
    return f'<div style="display: flex; align-items: center; gap: 15px;">{edit_link}{delete_button}</div>'

def icon_pencil():
    return '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 4px; vertical-align: -2px;"><path d="M12 20h9"></path><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path></svg>'

def icon_trash():
    return '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 4px; vertical-align: -2px;"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>'

def icon_share():
    return '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 4px; vertical-align: -2px;"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path></svg>'

@app.get("/", response_class=HTMLResponse)
async def index(session: str | None = Cookie(default=None), db: AsyncSession = Depends(get_db)):
    user = await load_user(db, session)
    if not user:
        content = """
        <div style="text-align: center; padding: 50px 20px;">
            <h1 style="color: #1e3a8a;">Добро пожаловать в Voting App!</h1>
            <p style="font-size: 1.2rem; color: #4b5563; margin-bottom: 30px;">
                Создавайте опросы, проходите тесты и узнавайте мнения других.
            </p>
            <p style="font-size: 1.1rem;">
                Чтобы просмотреть доступные опросы, 
                <a href="/login">войдите</a> или <a href="/register">зарегистрируйтесь</a>.
            </p>
        </div>
        """
        return page(title="Главная", content=content, user=user)

    res = await db.execute(select(Poll).where(Poll.is_active == True).order_by(Poll.created_at.desc()).limit(50))
    polls = res.scalars().all()
    
    if polls:
        items = ""
        for p in polls:
            actions_html = ""
            if p.author_id == user.id:
                edit_link = f'<a href="/polls/{p.id}/edit" style="font-size: 0.85rem; color: #6b7280; text-decoration: none; display: flex; align-items: center;">{icon_pencil()}Ред.</a>'
                delete_button = f'''
                <form method="post" action="/polls/{p.id}/delete" style="display: inline; margin: 0;" onsubmit="return confirm('Вы уверены, что хотите удалить опрос?');">
                    <button type="submit" style="background: none; border: none; color: #ef4444; font-size: 0.85rem; cursor: pointer; padding: 0; display: flex; align-items: center; font-family: inherit;">
                        {icon_trash()}Удал.
                    </button>
                </form>
                '''
                actions_html = action_icons(edit_link, delete_button)
            
            items += (
                f'<li>'
                f'<a href="/polls/{p.id}"><b>{p.title}</b></a>'
                f'<div style="display: flex; align-items: center;">'
                f'{actions_html}'
                f'<span class="date" style="margin-left: 15px;">{p.created_at.strftime("%d.%m.%Y")}</span>'
                f'</div>'
                f'</li>'
            )
        content = render("index.html", content=f"<h1>Активные опросы</h1><ul class='poll-list'>{items}</ul>")
    else:
        content = render("index.html", content='<h1>Активные опросы</h1><p>Пока нет опросов. <a href="/polls/new">Создайте первый!</a></p>')
    return page(title="Главная", content=content, user=user)

@app.get("/register", response_class=HTMLResponse)
async def register_form(request: Request, session: str | None = Cookie(default=None), db: AsyncSession = Depends(get_db)):
    user = await load_user(db, session)
    next_url = request.query_params.get("next", "")
    return page(title="Регистрация", content=render("register.html", error_block="", next_url=next_url), user=user)

@app.post("/register")
async def register(username: str = Form(...), password: str = Form(...), next_url: str = Form(""), db: AsyncSession = Depends(get_db)):
    username = username.strip()
    err = ""
    if len(username) < 3 or len(password) < 6: err = "Имя ≥3 символов, пароль ≥6"
    else:
        exists = await db.execute(select(User).where(User.username == username))
        if exists.scalar_one_or_none(): err = "Пользователь уже существует"
    if err: return page(title="Регистрация", content=render("register.html", error_block=error_block(err), next_url=next_url), user=None, status_code=400)
    user = User(username=username, password_hash=hash_password(password))
    db.add(user); await db.commit(); await db.refresh(user)
    redirect_to = next_url if next_url else "/"
    resp = RedirectResponse(redirect_to, status_code=303)
    resp.set_cookie("session", create_session(user.id), httponly=True, samesite="lax")
    return resp

@app.get("/login", response_class=HTMLResponse)
async def login_form(request: Request, session: str | None = Cookie(default=None), db: AsyncSession = Depends(get_db)):
    user = await load_user(db, session)
    next_url = request.query_params.get("next", "")
    return page(title="Вход", content=render("login.html", error_block="", next_url=next_url), user=user)

@app.post("/login")
async def login(username: str = Form(...), password: str = Form(...), next_url: str = Form(""), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(User).where(User.username == username))
    user = res.scalar_one_or_none()
    if not user or not verify_password(password, user.password_hash):
        return page(title="Вход", content=render("login.html", error_block=error_block("Неверные данные"), next_url=next_url), user=None, status_code=400)
    redirect_to = next_url if next_url else "/"
    resp = RedirectResponse(redirect_to, status_code=303)
    resp.set_cookie("session", create_session(user.id), httponly=True, samesite="lax")
    return resp

@app.get("/logout")
async def logout():
    resp = RedirectResponse("/", status_code=303)
    resp.delete_cookie("session")
    return resp

@app.get("/polls/new", response_class=HTMLResponse)
async def new_poll_form(session: str | None = Cookie(default=None), db: AsyncSession = Depends(get_db)):
    user = await load_user(db, session)
    if not user: return RedirectResponse("/login", status_code=303)
    return page(title="Новый опрос", content=render("poll_new.html", error_block=""), user=user)

@app.post("/polls/new")
async def create_poll(
    title: str = Form(...), description: str = Form(""), 
    is_test: str = Form(None), allow_retake: str = Form(None), time_limit: str = Form(""),
    questions_json: str = Form(...),
    session: str | None = Cookie(default=None), db: AsyncSession = Depends(get_db)
):
    user = await load_user(db, session)
    if not user: return RedirectResponse("/login", status_code=303)
    try: q_data = json.loads(questions_json)
    except: return page(title="Ошибка", content=error_block("Неверный формат данных"), user=user, status_code=400)
    
    t_limit = int(time_limit) if time_limit.strip() else None
    if t_limit and (t_limit < 1 or t_limit > 60): t_limit = None

    poll = Poll(
        title=title.strip(), description=description.strip(), author_id=user.id, 
        is_test=bool(is_test), allow_retake=bool(allow_retake), time_limit=t_limit
    )
    db.add(poll); await db.flush()
    
    for q in q_data:
        if not q.get("text", "").strip(): continue
        # ИСПРАВЛЕНИЕ: Берем тип из JSON
        question = Question(
            poll_id=poll.id, 
            text=q["text"].strip(), 
            question_type=q.get("type", "single") 
        )
        db.add(question); await db.flush()
        correct_idx = q.get("correct", -1)
        for idx, opt in enumerate(q.get("options", [])):
            if opt.strip():
                is_cor = (idx == correct_idx) if poll.is_test else False
                db.add(Option(question_id=question.id, text=opt.strip(), is_correct=is_cor))
    await db.commit()
    return RedirectResponse(f"/polls/{poll.id}", status_code=303)

@app.get("/polls/{poll_id}", response_class=HTMLResponse)
async def view_poll(poll_id: int, session: str | None = Cookie(default=None), db: AsyncSession = Depends(get_db)):
    user = await load_user(db, session)
    res = await db.execute(select(Poll).options(selectinload(Poll.questions).selectinload(Question.options), selectinload(Poll.author)).where(Poll.id == poll_id))
    poll = res.scalar_one_or_none()
    if not poll: raise HTTPException(404, "Опрос не найден")
    
    voted = False
    if user:
        v = await db.execute(select(Vote).join(Question).where(Question.poll_id == poll_id, Vote.user_id == user.id).limit(1))
        voted = v.scalar_one_or_none() is not None
        
    description_block = f'<p class="desc">{poll.description}</p>' if poll.description else ""
    
    share_button = f'''
    <button onclick="copyLink()" style="background: none; border: none; color: #6b7280; font-size: 0.85rem; cursor: pointer; padding: 0; display: flex; align-items: center; font-family: inherit;">
        {icon_share()}Поделиться
    </button>
    <script>
        function copyLink() {{
            navigator.clipboard.writeText(window.location.href).then(function() {{
                alert('Ссылка скопирована в буфер обмена!');
            }});
        }}
    </script>
    '''

    edit_link = ""
    delete_button = ""
    if user and poll.author_id == user.id:
        edit_link = f'<a href="/polls/{poll.id}/edit" style="font-size: 0.85rem; color: #6b7280; text-decoration: none; display: flex; align-items: center;">{icon_pencil()}Ред.</a>'
        delete_button = f'''
        <form method="post" action="/polls/{poll.id}/delete" style="display: inline; margin: 0;" onsubmit="return confirm('Вы уверены, что хотите удалить опрос?');">
            <button type="submit" style="background: none; border: none; color: #ef4444; font-size: 0.85rem; cursor: pointer; padding: 0; display: flex; align-items: center; font-family: inherit;">
                {icon_trash()}Удал.
            </button>
        </form>
        '''

    if voted and not poll.allow_retake:
        body = '<div class="notice">Вы уже прошли этот опрос. Повторное прохождение запрещено автором.</div><p><a href="/polls/'+str(poll.id)+'/results">Посмотреть результаты →</a></p>'
    elif user:
        timer_script = ""
        timer_html = ""
        if poll.time_limit:
            timer_html = f'<div id="timer" style="font-size: 20px; font-weight: bold; color: #ef4444; margin-bottom: 15px;">Осталось: {poll.time_limit}:00</div>'
            timer_script = f'''
            <script>
                let timeLeft = {poll.time_limit} * 60;
                let timerElement = document.getElementById('timer');
                let timerId = setInterval(function() {{
                    timeLeft--;
                    let m = Math.floor(timeLeft / 60);
                    let s = timeLeft % 60;
                    timerElement.innerHTML = 'Осталось: ' + m + ':' + (s < 10 ? '0' : '') + s;
                    if (timeLeft <= 0) {{
                        clearInterval(timerId);
                        document.getElementById('poll-form').submit();
                    }}
                }}, 1000);
            </script>
            '''
            
        form_html = f'<form method="post" action="/polls/{poll.id}/vote" class="card" id="poll-form">{timer_html}'
        for q in poll.questions:
            # ИСПРАВЛЕНИЕ: Определяем тип поля (radio или checkbox)
            input_type = "checkbox" if q.question_type == "multiple" else "radio"
            form_html += f'<div style="margin-bottom: 15px;"><b>{q.text}</b><br>'
            for o in q.options:
                form_html += f'<label class="radio"><input type="{input_type}" name="q_{q.id}" value="{o.id}"> {o.text}</label>'
            form_html += '</div>'
        form_html += '<button type="submit">Ответить</button></form>' + timer_script
        body = form_html
    else:
        body = f'<p>Чтобы пройти, <a href="/login?next=/polls/{poll.id}">войдите</a> или <a href="/register?next=/polls/{poll.id}">зарегистрируйтесь</a>.</p>'
        
    content = render(
        "poll_vote.html", 
        title=poll.title, 
        description_block=description_block, 
        author=poll.author.username, 
        date=poll.created_at.strftime("%d.%m.%Y"), 
        body=body, 
        poll_id=poll.id,
        share_button=share_button,
        edit_link=edit_link,
        delete_button=delete_button
    )
    return page(title=poll.title, content=content, user=user)

@app.post("/polls/{poll_id}/vote")
async def vote(poll_id: int, request: Request, session: str | None = Cookie(default=None), db: AsyncSession = Depends(get_db)):
    user = await load_user(db, session)
    if not user: return RedirectResponse("/login", status_code=303)
    poll_res = await db.execute(select(Poll).where(Poll.id == poll_id))
    poll = poll_res.scalar_one_or_none()
    if poll and poll.allow_retake:
        await db.execute(delete(Vote).where(Vote.user_id == user.id, Vote.question_id.in_(select(Question.id).where(Question.poll_id == poll_id))))
        await db.commit()
    form_data = await request.form()
    
    # Обработка голосов (учитываем, что может быть несколько значений для checkbox)
    for key, value in form_data.items():
        if key.startswith("q_"):
            q_id = int(key[2:])
            existing = await db.execute(select(Vote).where(Vote.question_id == q_id, Vote.user_id == user.id))
            if existing.scalar_one_or_none(): continue
            
            # Если value — это список (checkbox), сохраняем каждый
            if isinstance(value, list):
                for opt_id in value:
                    db.add(Vote(question_id=q_id, option_id=int(opt_id), user_id=user.id))
            else:
                db.add(Vote(question_id=q_id, option_id=int(value), user_id=user.id))
                
    await db.commit()
    return RedirectResponse(f"/polls/{poll_id}/results", status_code=303)

@app.get("/polls/{poll_id}/results", response_class=HTMLResponse)
async def results(poll_id: int, session: str | None = Cookie(default=None), db: AsyncSession = Depends(get_db)):
    user = await load_user(db, session)
    poll_res = await db.execute(select(Poll).options(selectinload(Poll.questions).selectinload(Question.options)).where(Poll.id == poll_id))
    poll = poll_res.scalar_one_or_none()
    if not poll: raise HTTPException(404)
    content_html = f"<h1>{poll.title}</h1>"
    if poll.description: content_html += f'<p class="desc">{poll.description}</p>'
    if poll.is_test:
        correct_count = 0
        total_q = len(poll.questions)
        content_html += "<h3>Ваши результаты:</h3>"
        for q in poll.questions:
            user_vote_res = await db.execute(select(Vote).where(Vote.question_id == q.id, Vote.user_id == user.id))
            user_vote = user_vote_res.scalar_one_or_none()
            user_opt_id = user_vote.option_id if user_vote else None
            if user_opt_id:
                for o in q.options:
                    if o.id == user_opt_id and o.is_correct:
                        correct_count += 1
                        break
            content_html += f"<div style='margin-bottom: 20px;'><b>{q.text}</b><br><ul class='results' style='list-style:none; padding:0;'>"
            for o in q.options:
                color = "inherit"; icon = ""
                if o.is_correct: color = "#10b981"; icon = " ✅"
                elif o.id == user_opt_id and not o.is_correct: color = "#ef4444"; icon = " ❌"
                content_html += f"<li style='color: {color}; font-weight: {'bold' if o.id == user_opt_id or o.is_correct else 'normal'};'>{o.text}{icon}</li>"
            content_html += "</ul></div>"
        content_html += f"<h2 style='color: #1e3a8a;'>Правильных ответов: {correct_count} из {total_q}</h2>"
    else:
        for q in poll.questions:
            content_html += f"<h3>{q.text}</h3><ul class='results'>"
            rows = await db.execute(select(Option.id, Option.text, func.count(Vote.id)).outerjoin(Vote, Vote.option_id == Option.id).where(Option.question_id == q.id).group_by(Option.id, Option.text).order_by(Option.id))
            data = [{"text": r[1], "count": r[2]} for r in rows.all()]
            total = sum(r["count"] for r in data) or 1
            for r in data:
                pct = r["count"] * 100 // total
                content_html += f'<li><div class="row"><span>{r["text"]}</span><span class="num">{r["count"]} ({pct}%)</span></div><div class="bar-bg"><div class="bar" style="width: {pct}%"></div></div></li>'
            content_html += "</ul>"
    if poll.allow_retake:
        content_html += f'<p><a href="/polls/{poll.id}" style="font-weight: bold; color: #2563eb;">Пройти заново</a></p>'
    content_html += f'<p><a href="/">← К списку</a></p>'
    return page(title=f"Результаты — {poll.title}", content=content_html, user=user)

@app.get("/polls/{poll_id}/edit", response_class=HTMLResponse)
async def edit_poll_form(poll_id: int, session: str | None = Cookie(default=None), db: AsyncSession = Depends(get_db)):
    user = await load_user(db, session)
    if not user: return RedirectResponse("/login", status_code=303)
    res = await db.execute(select(Poll).options(selectinload(Poll.questions).selectinload(Question.options)).where(Poll.id == poll_id))
    poll = res.scalar_one_or_none()
    if not poll: raise HTTPException(404, "Опрос не найден")
    if poll.author_id != user.id: raise HTTPException(403, "Вы не автор этого опроса")
    questions_data = [{"text": q.text, "type": q.question_type, "options": [o.text for o in q.options], "correct": next((i for i, o in enumerate(q.options) if o.is_correct), -1)} for q in poll.questions]
    content = render("poll_edit.html", error_block="", poll_id=poll.id, title=poll.title, description=poll.description or "", is_test_checked="checked" if poll.is_test else "", allow_retake_checked="checked" if poll.allow_retake else "", use_timer_checked="checked" if poll.time_limit else "", time_limit=poll.time_limit or "", timer_block_style="" if poll.time_limit else "display: none;", questions_json=json.dumps(questions_data))
    return page(title="Редактирование", content=content, user=user)

@app.post("/polls/{poll_id}/edit")
async def edit_poll(poll_id: int, title: str = Form(...), description: str = Form(""), is_test: str = Form(None), allow_retake: str = Form(None), time_limit: str = Form(""), questions_json: str = Form(...), session: str | None = Cookie(default=None), db: AsyncSession = Depends(get_db)):
    user = await load_user(db, session)
    if not user: return RedirectResponse("/login", status_code=303)
    res = await db.execute(select(Poll).where(Poll.id == poll_id))
    poll = res.scalar_one_or_none()
    if not poll or poll.author_id != user.id: raise HTTPException(403, "Нет доступа")
    try: q_data = json.loads(questions_json)
    except: return page(title="Ошибка", content=error_block("Неверный формат данных"), user=user, status_code=400)
    t_limit = int(time_limit) if time_limit.strip() else None
    if t_limit and (t_limit < 1 or t_limit > 60): t_limit = None
    poll.title = title.strip(); poll.description = description.strip(); poll.is_test = bool(is_test); poll.allow_retake = bool(allow_retake); poll.time_limit = t_limit
    await db.execute(delete(Question).where(Question.poll_id == poll.id)); await db.flush()
    for q in q_data:
        if not q.get("text", "").strip(): continue
        # ИСПРАВЛЕНИЕ: Берем тип из JSON при редактировании
        question = Question(poll_id=poll.id, text=q["text"].strip(), question_type=q.get("type", "single"))
        db.add(question); await db.flush()
        correct_idx = q.get("correct", -1)
        for idx, opt in enumerate(q.get("options", [])):
            if opt.strip():
                is_cor = (idx == correct_idx) if poll.is_test else False
                db.add(Option(question_id=question.id, text=opt.strip(), is_correct=is_cor))
    await db.commit()
    return RedirectResponse(f"/polls/{poll.id}", status_code=303)

@app.post("/polls/{poll_id}/delete")
async def delete_poll(poll_id: int, session: str | None = Cookie(default=None), db: AsyncSession = Depends(get_db)):
    user = await load_user(db, session)
    if not user: return RedirectResponse("/login", status_code=303)
    res = await db.execute(select(Poll).where(Poll.id == poll_id))
    poll = res.scalar_one_or_none()
    if not poll: raise HTTPException(404, "Опрос не найден")
    if poll.author_id != user.id: raise HTTPException(403, "Вы не можете удалить этот опрос")
    await db.delete(poll); await db.commit()
    return RedirectResponse("/", status_code=303)