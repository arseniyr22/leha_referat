import { useState, useEffect, useRef } from "react";
import { X, Star, ChevronDown, Menu, Download, ArrowRight } from "lucide-react";
const Close = X;

const C = {
  bg:          "#FFFFFF",
  offwhite:    "#F5F5F2",
  black:       "#0A0A09",
  gray:        "#5A5A58",
  grayMid:     "#8A8A88",
  grayLight:   "#CCCCCA",
  border:      "#E0E0DD",
  borderStrong:"#0A0A09",
  headGray:    "#B0B0A8",
  headDark:    "#5C5C58",
};

const DIRECTIONS = [
  { code:"38.03.01", label:"Экономика" },
  { code:"38.03.02", label:"Менеджмент" },
  { code:"38.03.04", label:"Государственное и муниципальное управление" },
  { code:"38.03.05", label:"Бизнес-информатика" },
  { code:"40.03.01", label:"Юриспруденция" },
  { code:"41.03.04", label:"Политология" },
  { code:"41.03.05", label:"Международные отношения" },
  { code:"42.03.01", label:"Реклама и связи с общественностью" },
  { code:"45.03.01", label:"Филология" },
  { code:"45.03.02", label:"Лингвистика" },
  { code:"46.03.01", label:"История" },
  { code:"47.03.01", label:"Философия" },
  { code:"37.03.01", label:"Психология" },
  { code:"39.03.01", label:"Социология" },
  { code:"44.03.01", label:"Педагогическое образование" },
  { code:"44.03.02", label:"Психолого-педагогическое образование" },
  { code:"09.03.01", label:"Информатика и вычислительная техника" },
  { code:"09.03.03", label:"Прикладная информатика" },
  { code:"10.03.01", label:"Информационная безопасность" },
  { code:"15.03.01", label:"Машиностроение" },
  { code:"08.03.01", label:"Строительство" },
  { code:"13.03.02", label:"Электроэнергетика и электротехника" },
  { code:"20.03.01", label:"Техносферная безопасность" },
  { code:"21.03.01", label:"Нефтегазовое дело" },
  { code:"21.03.02", label:"Землеустройство и кадастры" },
  { code:"23.03.01", label:"Технология транспортных процессов" },
  { code:"27.03.02", label:"Управление качеством" },
  { code:"31.05.01", label:"Лечебное дело" },
  { code:"33.05.01", label:"Фармация" },
  { code:"34.03.01", label:"Сестринское дело" },
  { code:"05.03.06", label:"Экология и природопользование" },
  { code:"06.03.01", label:"Биология" },
  { code:"03.03.01", label:"Прикладная математика и физика" },
];

const WORK_TYPES = [
  { id:"essay",        label:"Сочинение",      price:197,  pages:"5–10" },
  { id:"abstract",     label:"Реферат",         price:397,  pages:"20–25" },
  { id:"essay2",       label:"Эссе",            price:297,  pages:"5–10" },
  { id:"report",       label:"Доклад",          price:297,  pages:"10–15" },
  { id:"course",       label:"Курсовая",        price:897,  pages:"35–45" },
  { id:"diploma",      label:"ВКР / Диплом",    price:1890, pages:"60–80" },
  { id:"article",      label:"Научная статья",  price:697,  pages:"10–20" },
  { id:"school",       label:"Школьный проект", price:297,  pages:"10–20" },
  { id:"presentation", label:"Презентация",     price:497,  pages:"15–20 сл." },
  { id:"text",         label:"Текст",           price:197,  pages:"3–5" },
];

const AGENTS = [
  { name:"АГЕНТ СТРУКТУРЫ",         sub:"Structure",    desc:"Строит логичный план работы: введение, главы, параграфы, заключение — под конкретную тему и тип работы" },
  { name:"АГЕНТ КОНТЕНТА",          sub:"Content",      desc:"Генерирует полный академический текст по структуре: аргументы, примеры, анализ, выводы по каждому разделу" },
  { name:"АГЕНТ ДАННЫХ",            sub:"Data",         desc:"Находит актуальную статистику, цифры, исследования из открытых баз — Росстат, ЦБ РФ, научные журналы" },
  { name:"АГЕНТ ОФОРМЛЕНИЯ",        sub:"Formatting",   desc:"Приводит работу к стандарту ГОСТ: шрифты, отступы, нумерация, таблицы, рисунки, список литературы" },
  { name:"АГЕНТ УНИКАЛЬНОСТИ",      sub:"Uniqueness",   desc:"Перефразирует и реструктурирует текст до уникальности 85–95% в Антиплагиате без потери смысла" },
];

const FAQ_ITEMS = [
  { q:"Это точно не определят как ИИ?", a:"Да. Наш алгоритм переработки текста убирает все маркеры ИИ-генерации: нет шаблонных конструкций, нет одинаковой длины предложений, нет «роботских» переходов. В Антиплагиате не будет плашки «подозрительный текст» — только зелёные и жёлтые зоны." },
  { q:"Какая уникальность в Антиплагиате.ру?", a:"85–95% в зависимости от темы. Точная цифра зависит от дисциплины: технические и юридические темы — 85–90%, гуманитарные — до 95%." },
  { q:"За сколько будет готова моя работа?", a:"Работа генерируется автоматически и занимает от нескольких секунд до 10 минут — в зависимости от типа и объёма. Без очереди и ожидания исполнителя." },
  { q:"Можно ли сдать работу в любой вуз?", a:"Да. В базе 200+ вузов России с их методическими требованиями: МГУ, ВШЭ, МГИМО, РАНХиГС, МГТУ и другие. Оформление подстраивается автоматически." },
  { q:"Чем это лучше, чем просто попросить ChatGPT?", a:"ChatGPT не знает ГОСТ, не строит правильную структуру, даёт несуществующие источники и оставляет в тексте маркеры ИИ, которые видны в Антиплагиате. referat.io — специализированный инструмент именно для академических работ." },
  { q:"Источники в списке литературы реальные?", a:"Да. Агент данных подбирает только существующие источники 2020–2024 годов из научных баз. Никаких фантомных ссылок — каждый источник проверяется на доступность." },
  { q:"Можно ли редактировать результат?", a:"Да. Вы получаете файл Word, который можно редактировать как обычный документ — менять текст, добавлять свои данные, корректировать под конкретное задание." },
  { q:"Сколько это стоит?", a:"От 197₽ за сочинение до 1890₽ за ВКР. Без подписки, без скрытых доплат — платите один раз за конкретную работу. Первый план структуры — бесплатно, без регистрации." },
];

const UNIVERSITIES = [
  "МГУ","СПбГУ","ВШЭ","МГТУ им. Баумана","МГИМО","РАНХиГС","РУДН","ИТМО",
  "Финансовый университет","МФТИ","УрФУ","КФУ","НГУ","ТГУ","СПбПУ",
  "РГЭУ РИНХ","КубГУ","ВГУ","ДВФУ","ЮФУ","СФУ","ТюмГУ","НИЯУ МИФИ",
];

const EXAMPLES = [
  { type:"Курсовая", topic:"Цифровая трансформация государственного управления в РФ",  pages:40, unique:88, subject:"Государственное управление" },
  { type:"Реферат",  topic:"Роль международных организаций в урегулировании конфликтов", pages:23, unique:90, subject:"Международные отношения" },
  { type:"ВКР",      topic:"Оценка инвестиционной привлекательности регионов России",     pages:69, unique:86, subject:"Региональная экономика" },
  { type:"Эссе",     topic:"Суверенитет государства в условиях глобализации",             pages:9,  unique:93, subject:"Политология" },
  { type:"Курсовая", topic:"Трансформация рынка труда под влиянием автоматизации",        pages:38, unique:85, subject:"Экономика труда" },
  { type:"Реферат",  topic:"Правовое регулирование персональных данных в цифровую эпоху", pages:25, unique:91, subject:"Информационное право" },
];

const REVIEWS = [
  { nick:"Станислав",  platform:"МГИМО · Международные отношения",    text:"Курсовую по международному праву сделал за 10 минут. Структура идеальная, источники реальные." },
  { nick:"Алина",      platform:"ВШЭ · Экономика",                    text:"Антиплагиат показал 91%. Преподаватель не придрался ни к одному источнику." },
  { nick:"Дмитрий",    platform:"МГТУ им. Баумана · Машиностроение",  text:"ВКР на 68 страниц. Получил на почту через 8 минут. Оформление по ГОСТу с первого раза — сам бы дольше делал." },
  { nick:"Полина",     platform:"РАНХиГС · Государственное управление",text:"Реферат по конституционному праву — 89% уникальность. Сдала без замечаний." },
  { nick:"Артём",      platform:"СПбГУ · Юриспруденция",              text:"Список литературы — всё реальное, всё 2022–2024. Первый раз вижу такое от ИИ." },
  { nick:"Вероника",   platform:"МГУ · Социология",                   text:"Сравнивала с ChatGPT — небо и земля. Здесь реальная академическая работа, не пересказ." },
  { nick:"Игорь",      platform:"РУДН · Менеджмент",                  text:"Курсовая по финансам предприятия: таблицы, расчёты, диаграммы — всё на месте." },
  { nick:"Наташа",     platform:"ИТМО · Прикладная математика",        text:"Не ожидала что техническая работа получится так хорошо. Формулы оформлены правильно." },
];

// ─── STYLES ───────────────────────────────────────────────────────────────────
const GS = `
  @import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@300;400;500;600;700;800;900&family=Barlow:wght@300;400;500&display=swap');
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  html { scroll-behavior: smooth; }
  body { background: #fff; color: #0A0A09; font-family: 'Barlow', sans-serif; font-weight: 300; }
  ::selection { background: #0A0A09; color: #fff; }
  .H { font-family: 'Barlow Condensed', sans-serif; font-weight: 800; text-transform: uppercase; letter-spacing: -0.01em; line-height: 0.92; }
  .LBL { font-family: 'Barlow Condensed', sans-serif; font-weight: 600; text-transform: uppercase; letter-spacing: 0.14em; font-size: 11px; }
  .SUB { font-family: 'Barlow Condensed', sans-serif; font-weight: 400; text-transform: uppercase; letter-spacing: 0.06em; }
  input, select, button, textarea { font-family: 'Barlow', sans-serif; }
  @keyframes spin { to { transform: rotate(360deg); } }
  @keyframes mL { from{transform:translateX(0)} to{transform:translateX(-50%)} }
  @keyframes mR { from{transform:translateX(-50%)} to{transform:translateX(0)} }
  @keyframes fI { from{opacity:0;transform:translateX(-5px)} to{opacity:1;transform:translateX(0)} }
  @media(max-width:900px){
    .desk{display:none!important}
    .mob{display:flex!important}
    .grid3{grid-template-columns:1fr!important}
    .grid5{grid-template-columns:1fr 1fr!important}
    .gridStats{grid-template-columns:1fr 1fr!important}
  }
`;

function useInView(ref) {
  const [v,set]=useState(false);
  useEffect(()=>{
    if(!ref.current)return;
    const o=new IntersectionObserver(([e])=>{if(e.isIntersecting)set(true)},{threshold:0.08});
    o.observe(ref.current);
    return()=>o.disconnect();
  },[ref]);
  return v;
}
function Reveal({children,style={},delay=0}){
  const ref=useRef(null);
  const v=useInView(ref);
  return(
    <div ref={ref} style={{opacity:v?1:0,transform:v?"translateY(0)":"translateY(20px)",transition:`opacity 0.55s ease ${delay}s,transform 0.55s ease ${delay}s`,...style}}>
      {children}
    </div>
  );
}

const HR  = ({style={}}) => <div style={{height:1,background:C.borderStrong,...style}}/>;
const HRL = ({style={}}) => <div style={{height:1,background:C.border,...style}}/>;

function Tag({children}){
  return(
    <div className="LBL" style={{color:C.grayMid,marginBottom:10,display:"flex",alignItems:"center",gap:10}}>
      <div style={{width:20,height:1,background:C.grayLight}}/>
      {children}
      <div style={{width:20,height:1,background:C.grayLight}}/>
    </div>
  );
}

// ─── HEADER ───────────────────────────────────────────────────────────────────
function Header({scrolled,menuOpen,setMenuOpen,onOrder}){
  const go=id=>{document.getElementById(id)?.scrollIntoView({behavior:"smooth"});setMenuOpen(false);};
  return(
    <>
      <div style={{background:C.black,padding:"7px 20px",textAlign:"center"}}>
        <span className="LBL" style={{color:"#fff",fontSize:10,letterSpacing:"0.2em"}}>
          ВСТРОЕН АНТИ-AI ДЕТЕКТОР — РАБОТАЕТ ПО УМОЛЧАНИЮ ДЛЯ ВСЕХ РАБОТ
        </span>
      </div>

      <header style={{
        position:"sticky",top:0,zIndex:100,
        background:"rgba(255,255,255,0.97)",
        backdropFilter:"blur(12px)",
        borderBottom:`1px solid ${scrolled?C.black:C.border}`,
        transition:"border-color 0.3s",
      }}>
        <div style={{maxWidth:1200,margin:"0 auto",padding:"0 32px",display:"flex",alignItems:"center",justifyContent:"space-between",height:56}}>
          <div onClick={()=>go("top")} style={{cursor:"pointer"}}>
            <span className="H" style={{fontSize:20,letterSpacing:"-0.02em",color:C.headDark}}>REFERAT</span><span style={{fontFamily:"'Barlow Condensed',sans-serif",fontWeight:300,fontSize:20,textTransform:"uppercase",letterSpacing:"-0.02em",color:C.black}}>.IO</span>
          </div>

          <nav className="desk" style={{display:"flex",gap:32}}>
            {[["ЦЕНЫ","prices"],["FAQ","faq"],["ОТЗЫВЫ","reviews"]].map(([l,id])=>(
              <button key={id} onClick={()=>go(id)} className="LBL"
                style={{background:"none",border:"none",color:C.grayMid,cursor:"pointer",fontSize:10,transition:"color 0.15s"}}
                onMouseEnter={e=>e.target.style.color=C.black}
                onMouseLeave={e=>e.target.style.color=C.grayMid}>{l}</button>
            ))}
          </nav>

          <div style={{display:"flex",alignItems:"center",gap:12}}>
            <button onClick={onOrder}
              style={{background:"none",color:C.black,padding:"8px 22px",fontFamily:"'Barlow Condensed',sans-serif",fontWeight:700,fontSize:12,textTransform:"uppercase",letterSpacing:"0.12em",border:`1px solid ${C.black}`,transition:"all 0.15s",cursor:"pointer"}}
              onMouseEnter={e=>{e.currentTarget.style.background=C.black;e.currentTarget.style.color="#fff";}}
              onMouseLeave={e=>{e.currentTarget.style.background="none";e.currentTarget.style.color=C.black;}}>
              ПОПРОБОВАТЬ
            </button>
            <button className="mob" onClick={()=>setMenuOpen(!menuOpen)}
              style={{background:"none",border:"none",cursor:"pointer",display:"none",color:C.black,padding:4}}>
              {menuOpen?<Close size={20}/>:<Menu size={20}/>}
            </button>
          </div>
        </div>
      </header>

      {menuOpen&&(
        <div style={{position:"fixed",top:91,left:0,right:0,bottom:0,background:"#fff",zIndex:99,padding:"40px 32px",borderTop:`1px solid ${C.black}`}}>
          {[["ЦЕНЫ","prices"],["FAQ","faq"],["ОТЗЫВЫ","reviews"]].map(([l,id])=>(
            <div key={id} style={{borderBottom:`1px solid ${C.border}`}}>
              <button onClick={()=>go(id)} className="H"
                style={{background:"none",border:"none",fontSize:44,cursor:"pointer",color:C.black,padding:"16px 0",display:"block",width:"100%",textAlign:"left"}}>
                {l}
              </button>
            </div>
          ))}
        </div>
      )}
    </>
  );
}

// ─── HERO ─────────────────────────────────────────────────────────────────────
function Hero({count,onOrder}){
  const [topic,setTopic]=useState("");
  const [workType,setWorkType]=useState("course");
  const [direction,setDirection]=useState("38.03.01");

  const go=()=>onOrder({topic,workType,direction});

  return(
    <section id="top" style={{background:"#fff",borderBottom:`1px solid ${C.black}`,position:"relative",overflow:"hidden"}}>

      <div style={{maxWidth:1200,margin:"0 auto",padding:"48px 32px 64px",width:"100%",position:"relative",zIndex:1}}>

        {/* META LINE */}
        <div style={{display:"flex",alignItems:"center",gap:14,marginBottom:20,flexWrap:"wrap"}}>
          {["НЕЙРОСЕТЬ ДЛЯ СТУДЕНТОВ","АНТИПЛАГИАТ 90%+","ГОСТ ОФОРМЛЕНИЕ","РЕАЛЬНЫЕ ИСТОЧНИКИ"].map((t,i)=>(
            <div key={i} style={{display:"flex",alignItems:"center",gap:14}}>
              <span className="LBL" style={{color:C.gray,fontSize:10}}>{t}</span>
              {i<3&&<div style={{width:1,height:10,background:C.grayLight}}/>}
            </div>
          ))}
        </div>

        <HR/>

        {/* GIANT HEADLINE */}
        <div style={{padding:"28px 0 24px"}}>
          <h1 className="H" style={{fontSize:"clamp(80px,14vw,200px)",lineHeight:0.88,marginBottom:4,color:C.headGray}}>
            REFERAT
          </h1>
          <div style={{display:"flex",alignItems:"flex-end",gap:32,flexWrap:"wrap"}}>
            <h1 className="H" style={{fontSize:"clamp(80px,14vw,200px)",lineHeight:0.88,color:C.black}}>
              .IO
            </h1>
            <div style={{paddingBottom:10,maxWidth:340}}>
              <p style={{fontSize:14,color:C.gray,lineHeight:1.65,fontWeight:300}}>
                Академические работы с уникальностью более 90%.
                Результат в течение 10 минут после оформления заказа.
                Оформление по ГОСТ. Реальные источники.
              </p>
            </div>
          </div>
        </div>

        <HR/>

        {/* STATS */}
        <div className="gridStats" style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",borderLeft:`1px solid ${C.border}`,margin:"0 0 28px"}}>
          {[["1 000+","РАБОТ СДАНО"],["85–95%","УНИКАЛЬНОСТЬ"],["5–10 МИН","НА РАБОТУ"],["200+","ВУЗОВ В БАЗЕ"]].map(([n,l],i)=>(
            <div key={i} style={{padding:"18px 22px",borderRight:`1px solid ${C.border}`,borderTop:`1px solid ${C.border}`,borderBottom:`1px solid ${C.border}`}}>
              <div className="H" style={{fontSize:34,color:C.headGray,marginBottom:3}}>{n}</div>
              <div className="LBL" style={{color:C.gray,fontSize:10}}>{l}</div>
            </div>
          ))}
        </div>

        {/* FORM */}
        <div style={{border:`1px solid ${C.black}`,maxWidth:680}}>
          <div className="LBL" style={{background:C.black,color:"#fff",padding:"10px 20px",fontSize:10,letterSpacing:"0.18em"}}>
            ГЕНЕРАТОР РАБОТ
          </div>
          <div style={{padding:20}}>
            <div style={{display:"flex",gap:8,flexWrap:"wrap",marginBottom:8}}>
              <select value={workType} onChange={e=>setWorkType(e.target.value)}
                style={{padding:"10px 12px",border:`1px solid ${C.border}`,background:C.offwhite,color:C.black,fontSize:13,cursor:"pointer",outline:"none",flexShrink:0}}>
                {WORK_TYPES.map(w=><option key={w.id} value={w.id}>{w.label}</option>)}
              </select>
              <select value={direction} onChange={e=>setDirection(e.target.value)}
                style={{padding:"10px 12px",border:`1px solid ${C.border}`,background:C.offwhite,color:C.black,fontSize:13,cursor:"pointer",outline:"none",flex:1,minWidth:160}}>
                {DIRECTIONS.map(d=><option key={d.code} value={d.code}>{d.code} · {d.label}</option>)}
              </select>
            </div>
            <input value={topic} onChange={e=>setTopic(e.target.value)}
              placeholder="Введите тему вашей работы..."
              style={{width:"100%",marginBottom:8,padding:"10px 12px",border:`1px solid ${C.border}`,background:C.offwhite,color:C.black,fontSize:13,outline:"none"}}/>
            <button onClick={go}
              style={{width:"100%",padding:"12px 24px",background:C.black,border:`1px solid ${C.black}`,color:"#fff",fontFamily:"'Barlow Condensed',sans-serif",fontWeight:700,fontSize:14,textTransform:"uppercase",letterSpacing:"0.12em",cursor:"pointer",transition:"all 0.15s",display:"flex",alignItems:"center",justifyContent:"center",gap:8}}>
              СГЕНЕРИРОВАТЬ →
            </button>
          </div>
          <div style={{borderTop:`1px solid ${C.border}`,padding:"9px 20px",display:"flex",gap:24,flexWrap:"wrap"}}>
            <span className="LBL" style={{color:C.grayMid,fontSize:10}}>СГЕНЕРИРОВАНО РАБОТ: <strong style={{color:C.black}}>1 078</strong></span>
            {[["IRecommend","4.9"],["Яндекс","4.9"],["Отзовик","5.0"]].map(([p,r])=>(
              <span key={p} className="LBL" style={{color:C.grayMid,fontSize:10}}>{p} <strong style={{color:C.black}}>{r}★</strong></span>
            ))}
          </div>
        </div>

        {/* checklist */}
        <div style={{marginTop:20,display:"flex",gap:24,flexWrap:"wrap"}}>
          {["Без значка «подозрительный файл»","Актуальный список литературы","Оформление по ГОСТ + таблицы"].map((t,i)=>(
            <div key={i} style={{display:"flex",alignItems:"center",gap:8}}>
              <div style={{width:14,height:14,border:`1.5px solid ${C.black}`,display:"flex",alignItems:"center",justifyContent:"center",flexShrink:0}}>
                <div style={{width:7,height:7,background:C.black}}/>
              </div>
              <span style={{fontSize:13,color:C.gray,fontWeight:300}}>{t}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─── DEMO ─────────────────────────────────────────────────────────────────────
const CHAT_MESSAGES = [
  { from:"user", text:"Курсовая · 38.03.04 Государственное и муниципальное управление\n\nТема: Цифровая трансформация государственного управления в РФ" },
  { from:"bot",  text:"Анализирую тему и направление подготовки. Формирую академическую структуру..." },
  { from:"bot",  text:`КУРСОВАЯ РАБОТА

Тема: Цифровая трансформация государственного управления в Российской Федерации
Направление: 38.03.04 ГМУ

СОДЕРЖАНИЕ

Введение ........................................................ 3
  — Актуальность. Степень научной разработанности.
  — Цель, задачи, объект, предмет исследования.
  — Методологическая база. Структура работы.

Глава 1. Теоретико-методологические основы цифровой трансформации публичного управления
  §1.1. Концептуальный аппарат: е-Government, Digital State, GovTech .... 7
  §1.2. Зарубежный опыт институционализации цифрового государства ........ 12
       (Эстония, Сингапур, Республика Корея: сравнительный анализ)

Глава 2. Институциональная среда цифровизации государственного управления в России
  §2.1. Нормативно-правовая база: Федеральный закон №149-ФЗ, нацпроект
        «Цифровая экономика», Стратегия развития ИТ до 2036 г. ............ 18
  §2.2. Ключевые платформы: ЕСИА / Госуслуги, СМЭВ, ГАС «Управление»,
        система межведомственного электронного взаимодействия .............. 24
  §2.3. Эмпирический анализ эффективности: индикаторы ООН e-Government
        Development Index, данные Росстата 2021–2024 гг. .................. 30

Глава 3. Проблемы и перспективы цифровой трансформации публичного управления
  §3.1. Институциональные барьеры и риски: цифровое неравенство,
        проблемы кибербезопасности, дефицит кадров ........................ 36
  §3.2. Направления совершенствования государственной цифровой политики
        на основе анализа нормативных документов и экспертных оценок ...... 41

Заключение ...................................................... 47
Список использованных источников и литературы (28 источников) ......... 50
  — Нормативно-правовые акты: 6 источников
  — Монографии и научные статьи: 14 источников (2019–2024)
  — Статистические и аналитические материалы: 8 источников` },
  { from:"user", text:"✓ Утверждаю структуру — начать генерацию" },
  { from:"bot",  text:"Отлично! Для получения готовой работы оплатите заказ:\n\n  ₽  897 ₽ — Курсовая · 38–45 стр. · ГОСТ Р 7.0.100-2018\n\nПосле оплаты работа поступит на ваш email в течение 5 минут." },
  { from:"bot",  text:"✅ Оплата подтверждена. Работа отправлена на ваш email.\n\nУникальность: 88%  ·  41 стр.  ·  Без плашки «подозрительный текст»" },
];

function DemoGenerator({onOrder}){
  const [step,setStep]=useState(0);
  const [running,setRunning]=useState(false);
  const chatRef=useRef(null);

  const start=()=>{setStep(0);setRunning(true);};

  useEffect(()=>{
    if(!running)return;
    if(step>=CHAT_MESSAGES.length){setRunning(false);return;}
    const delay = CHAT_MESSAGES[step]?.from==="bot" ? 900 : 500;
    const t=setTimeout(()=>setStep(s=>s+1), delay);
    return()=>clearTimeout(t);
  },[running,step]);

  useEffect(()=>{
    if(chatRef.current) chatRef.current.scrollTop = chatRef.current.scrollHeight;
  },[step]);

  return(
    <section id="demo" style={{background:C.offwhite,padding:"80px 32px",borderBottom:`1px solid ${C.black}`}}>
      <Reveal style={{maxWidth:760,margin:"0 auto"}}>
        <Tag>ДЕМО</Tag>
        <h2 className="H" style={{fontSize:"clamp(40px,6vw,72px)",marginBottom:24,lineHeight:0.92}}><span style={{color:C.headGray}}>КАК ЭТО</span><br/><span style={{color:C.black}}>РАБОТАЕТ</span></h2>
        <HR style={{marginBottom:0}}/>
        <div style={{border:`1px solid ${C.black}`,borderTop:"none"}}>
          {/* chat header */}
          <div style={{background:C.black,padding:"10px 20px",display:"flex",alignItems:"center",gap:10}}>
            <div style={{width:8,height:8,borderRadius:"50%",background:"#4ade80"}}/>
            <span className="LBL" style={{color:"rgba(255,255,255,0.7)",fontSize:10}}>REFERAT.IO — ОНЛАЙН</span>
          </div>
          {/* chat messages */}
          <div ref={chatRef} style={{padding:"20px 20px 10px",minHeight:200,maxHeight:380,overflowY:"auto",background:"#fff",display:"flex",flexDirection:"column",gap:12}}>
            {step===0&&(
              <div style={{color:C.grayLight,fontSize:13,textAlign:"center",padding:"40px 0"}}>Нажми «Запустить» чтобы увидеть демо</div>
            )}
            {CHAT_MESSAGES.slice(0,step).map((m,i)=>(
              <div key={i} style={{display:"flex",justifyContent:m.from==="user"?"flex-end":"flex-start",animation:"fI 0.3s ease"}}>
                {m.from==="bot"&&(
                  <div style={{width:28,height:28,background:C.black,borderRadius:0,display:"flex",alignItems:"center",justifyContent:"center",flexShrink:0,marginRight:8,alignSelf:"flex-end"}}>
                    <span style={{color:"#fff",fontSize:10,fontFamily:"'Barlow Condensed',sans-serif",fontWeight:700}}>R</span>
                  </div>
                )}
                <div style={{
                  maxWidth:"75%",
                  padding: m.text.includes("\n") ? "14px 18px" : "10px 14px",
                  background: m.from==="user" ? C.black : C.offwhite,
                  color: m.from==="user" ? "#fff" : C.black,
                  fontSize:13,
                  fontFamily: m.text.includes("Глава") ? "monospace" : "inherit",
                  lineHeight:1.6,
                  fontWeight:300,
                  whiteSpace:"pre-wrap",
                  border:`1px solid ${m.from==="user"?C.black:C.border}`,
                }}>
                  {m.text}
                </div>
              </div>
            ))}
            {running && step < CHAT_MESSAGES.length && CHAT_MESSAGES[step]?.from==="bot" && (
              <div style={{display:"flex",alignItems:"center",gap:8}}>
                <div style={{width:28,height:28,background:C.black,display:"flex",alignItems:"center",justifyContent:"center",flexShrink:0}}>
                  <span style={{color:"#fff",fontSize:10,fontFamily:"'Barlow Condensed',sans-serif",fontWeight:700}}>R</span>
                </div>
                <div style={{display:"flex",gap:4,padding:"10px 14px",background:C.offwhite,border:`1px solid ${C.border}`}}>
                  {[0,1,2].map(i=>(
                    <div key={i} style={{width:6,height:6,borderRadius:"50%",background:C.grayMid,animation:`spin 1s ease-in-out ${i*0.2}s infinite`}}/>
                  ))}
                </div>
              </div>
            )}
          </div>
          {/* controls */}
          <div style={{borderTop:`1px solid ${C.border}`,padding:"14px 20px",display:"flex",gap:8,background:"#fff"}}>
            {step < CHAT_MESSAGES.length ? (
              <button onClick={start} disabled={running}
                style={{flex:1,padding:"12px",background:running?C.offwhite:C.black,border:`1px solid ${running?C.border:C.black}`,color:running?C.gray:"#fff",fontFamily:"'Barlow Condensed',sans-serif",fontWeight:700,fontSize:14,textTransform:"uppercase",letterSpacing:"0.1em",cursor:running?"default":"pointer",transition:"all 0.15s"}}>
                {running?"ГЕНЕРИРУЮ...":"ЗАПУСТИТЬ ДЕМО"}
              </button>
            ) : (
              <button onClick={onOrder}
                style={{flex:1,padding:"14px",background:C.black,border:`1px solid ${C.black}`,color:"#fff",fontFamily:"'Barlow Condensed',sans-serif",fontWeight:700,fontSize:14,textTransform:"uppercase",letterSpacing:"0.12em",textAlign:"center",cursor:"pointer",display:"flex",alignItems:"center",justifyContent:"center",gap:8}}>
                ПЕРЕЙТИ К ГЕНЕРАЦИИ →
              </button>
            )}
          </div>
        </div>
      </Reveal>
    </section>
  );
}

// ─── REVIEWS ──────────────────────────────────────────────────────────────────
function Reviews(){
  return(
    <section id="reviews" style={{background:"#fff",padding:"80px 0",borderBottom:`1px solid ${C.black}`,overflow:"hidden"}}>
      <Reveal style={{padding:"0 32px",marginBottom:28}}>
        <Tag>ОТЗЫВЫ</Tag>
        <h2 className="H" style={{fontSize:"clamp(40px,6vw,72px)",lineHeight:0.92}}><span style={{color:C.headGray}}>ЧТО ГОВОРЯТ</span><br/><span style={{color:C.black}}>СТУДЕНТЫ</span></h2>
      </Reveal>
      <HR/>
      <div style={{overflow:"hidden",padding:"24px 0"}}>
        <div style={{display:"flex",gap:0,animation:"mL 36s linear infinite",width:"max-content"}}>
          {[...REVIEWS,...REVIEWS].map((r,i)=>(
            <div key={i} style={{width:270,flexShrink:0,borderRight:`1px solid ${C.border}`,padding:"20px 24px"}}>
              <div style={{display:"flex",alignItems:"center",gap:10,marginBottom:12}}>
                <div style={{width:30,height:30,background:C.black,display:"flex",alignItems:"center",justifyContent:"center",flexShrink:0}}>
                  <span style={{color:"#fff",fontFamily:"'Barlow Condensed',sans-serif",fontWeight:700,fontSize:13}}>{r.nick[0].toUpperCase()}</span>
                </div>
                <div>
                  <div style={{fontFamily:"'Barlow Condensed',sans-serif",fontWeight:700,fontSize:14,letterSpacing:"0.02em"}}>{r.nick}</div>
                  <div className="LBL" style={{color:C.grayMid,fontSize:9}}>{r.platform}</div>
                </div>
              </div>
              <p style={{fontSize:13,color:C.gray,lineHeight:1.55,fontWeight:300}}>{r.text}</p>
              <div style={{display:"flex",gap:2,marginTop:10}}>
                {[1,2,3,4,5].map(s=><Star key={s} size={10} fill={C.black} color={C.black}/>)}
              </div>
            </div>
          ))}
        </div>
      </div>
      <HR/>
      <div style={{display:"flex",flexWrap:"wrap",margin:"0 32px",borderLeft:`1px solid ${C.border}`}}>
        {[["IRecommend","4.9"],["Яндекс","4.9"],["Отзовик","5.0"]].map(([p,r],i)=>(
          <div key={i} style={{padding:"16px 28px",borderRight:`1px solid ${C.border}`,borderTop:`1px solid ${C.border}`,borderBottom:`1px solid ${C.border}`}}>
            <div className="H" style={{fontSize:28,color:C.headGray}}>{r} ★</div>
            <div className="LBL" style={{color:C.gray,fontSize:10}}>{p}</div>
          </div>
        ))}
      </div>
    </section>
  );
}

// ─── HOW IT WORKS ─────────────────────────────────────────────────────────────
function HowItWorks({onOrder}){
  const steps=[
    {num:"01",title:"ВВОДИШЬ\nТЕМУ",      desc:"Получаешь план и описание работы — бесплатно, за секунды. Без регистрации."},
    {num:"02",title:"ПРОВЕРЯЕШЬ\nСОДЕРЖАНИЕ", desc:"Редактируешь план, если хочешь что-то поменять. Всё гибко."},
    {num:"03",title:"РЕЗУЛЬТАТ НА\nПОЧТУ ЗА 10 МИН", desc:"По плану, с оформлением по ГОСТу и уникальностью 85–95%."},
  ];
  return(
    <section id="how" style={{background:C.offwhite,padding:"80px 32px",borderBottom:`1px solid ${C.black}`}}>
      <Reveal>
        <Tag>КАК ЭТО РАБОТАЕТ</Tag>
        <h2 className="H" style={{fontSize:"clamp(40px,6vw,72px)",marginBottom:28,lineHeight:0.92}}><span style={{color:C.headGray}}>3 ШАГА ДО</span><br/><span style={{color:C.black}}>ГОТОВОЙ РАБОТЫ</span></h2>
        <HR style={{marginBottom:0}}/>
        <div className="grid3" style={{display:"grid",gridTemplateColumns:"repeat(3,1fr)",background:C.black,gap:1}}>
          {steps.map((s,i)=>(
            <div key={i} style={{background:"#fff",padding:"36px 28px",transition:"background 0.2s",cursor:"default"}}
              onMouseEnter={e=>e.currentTarget.style.background=C.offwhite}
              onMouseLeave={e=>e.currentTarget.style.background="#fff"}>
              <div className="H" style={{fontSize:80,color:C.headGray,lineHeight:1,marginBottom:20,userSelect:"none"}}>{s.num}</div>
              <h3 className="H" style={{fontSize:26,color:C.headDark,marginBottom:12,whiteSpace:"pre-line"}}>{s.title}</h3>
              <p style={{fontSize:13,color:C.gray,lineHeight:1.65,fontWeight:300}}>{s.desc}</p>
            </div>
          ))}
        </div>
        <div style={{background:C.black,padding:"16px 28px",display:"flex",alignItems:"center",justifyContent:"space-between",flexWrap:"wrap",gap:8}}>
          <span className="H" style={{color:"#fff",fontSize:20}}>ПРЕПОДАВАТЕЛЬ ОЦЕНИТ КАЧЕСТВО ОФОРМЛЕНИЯ И СОДЕРЖАНИЯ</span>
          <span className="LBL" style={{color:C.grayMid,fontSize:10}}>РЕЗУЛЬТАТ ГАРАНТИРОВАН</span>
        </div>
      </Reveal>
    </section>
  );
}

// ─── UNIVERSITIES ─────────────────────────────────────────────────────────────
function Universities(){
  return(
    <section style={{background:"#fff",padding:"52px 0",borderBottom:`1px solid ${C.black}`,overflow:"hidden"}}>
      <Reveal style={{padding:"0 32px",marginBottom:24}}>
        <h2 className="H" style={{fontSize:"clamp(22px,3vw,40px)",color:C.headGray}}>
          СОЗДАЁМ РАБОТЫ ПО СТАНДАРТАМ <span style={{borderBottom:`3px solid ${C.black}`}}>200 ВУЗОВ</span> РОССИИ
        </h2>
      </Reveal>
      <HR style={{marginBottom:16}}/>
      {[1,-1].map((dir,row)=>(
        <div key={row} style={{overflow:"hidden",marginBottom:6}}>
          <div style={{display:"flex",gap:0,animation:`m${dir>0?"L":"R"} 30s linear infinite`,width:"max-content"}}>
            {[...UNIVERSITIES,...UNIVERSITIES].map((u,i)=>(
              <div key={i} style={{flexShrink:0,borderRight:`1px solid ${C.border}`,padding:"7px 20px"}}>
                <span className="SUB" style={{fontSize:13,color:C.gray,whiteSpace:"nowrap"}}>{u}</span>
              </div>
            ))}
          </div>
        </div>
      ))}
    </section>
  );
}

// ─── COMPARE ──────────────────────────────────────────────────────────────────
function CompareTable({onOrder}){
  const rows=[
    {crit:"Уникальность",      us:"85–95% в Антиплагиате",                    them:"20–40%, красные зоны по всему тексту"},
    {crit:"Плашка в Антиплаге",us:"Нет плашки «подозрительный текст»",        them:"Плашка «подозрительный текст» по всему документу"},
    {crit:"Источники",         us:"Реальные, 2020–2024, проверены",            them:"Несуществующие ссылки — не найдено в базах"},
    {crit:"Оформление ГОСТ",   us:"200+ вузов, авто-подстройка",               them:"Хаотичное, без стандартов"},
    {crit:"Структура работы",  us:"Логичная, под конкретную тему",             them:"Каждая глава как отдельный текст"},
    {crit:"Цена",              us:"от 197₽ за готовую работу",                 them:"$20/мес + VPN + ночь на доработку"},
  ];
  return(
    <section id="compare" style={{background:C.offwhite,padding:"80px 32px",borderBottom:`1px solid ${C.black}`}}>
      <Reveal style={{maxWidth:960,margin:"0 auto"}}>
        <Tag>СРАВНЕНИЕ</Tag>
        <h2 className="H" style={{fontSize:"clamp(40px,6vw,72px)",marginBottom:28,lineHeight:0.92}}><span style={{color:C.headGray}}>REFERAT.IO</span><br/><span style={{color:C.black}}>VS CHATGPT</span></h2>
        <HR style={{marginBottom:0}}/>
        <table style={{width:"100%",borderCollapse:"collapse"}}>
          <thead>
            <tr style={{background:C.black}}>
              {[["КРИТЕРИЙ"],["REFERAT.IO"],["CHATGPT / DEEPSEEK"]].map(([h],i)=>(
                <th key={i} style={{padding:"12px 20px",textAlign:"left"}}>
                  <span className="LBL" style={{color:i===1?"#fff":"rgba(255,255,255,0.4)",fontSize:10}}>{h}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r,i)=>(
              <tr key={i} style={{borderBottom:`1px solid ${C.border}`,background:i%2===0?"#fff":C.offwhite}}>
                <td style={{padding:"14px 20px",fontFamily:"'Barlow Condensed',sans-serif",fontWeight:700,fontSize:14,textTransform:"uppercase",letterSpacing:"0.04em",color:C.black}}>{r.crit}</td>
                <td style={{padding:"14px 20px",fontSize:13,color:C.black,fontWeight:400}}>{r.us}</td>
                <td style={{padding:"14px 20px",fontSize:13,color:C.grayMid,fontWeight:300}}>{r.them}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Reveal>
    </section>
  );
}

// ─── AGENTS ───────────────────────────────────────────────────────────────────
function AgentsSection(){
  return(
    <section id="agents" style={{background:"#fff",padding:"80px 32px",borderBottom:`1px solid ${C.black}`}}>
      <Reveal style={{maxWidth:1100,margin:"0 auto"}}>
        <Tag>АГЕНТЫ</Tag>
        <h2 className="H" style={{fontSize:"clamp(40px,6vw,72px)",marginBottom:8,lineHeight:0.92}}><span style={{color:C.headGray}}>КОМАНДА</span><br/><span style={{color:C.black}}>AI-АГЕНТОВ</span></h2>
        <p style={{fontSize:13,color:C.gray,marginBottom:28,fontWeight:300}}>Внутри работает 5 специализированных агентов</p>
        <HR style={{marginBottom:0}}/>
        <div className="grid5" style={{display:"grid",gridTemplateColumns:"repeat(5,1fr)",background:C.black,gap:1}}>
          {AGENTS.map((a,i)=>(
            <div key={i} style={{background:"#fff",padding:"26px 18px",transition:"background 0.2s",cursor:"default"}}
              onMouseEnter={e=>e.currentTarget.style.background=C.offwhite}
              onMouseLeave={e=>e.currentTarget.style.background="#fff"}>
              <div className="LBL" style={{color:C.grayMid,fontSize:9,marginBottom:10}}>{a.sub}</div>
              <h3 className="H" style={{fontSize:15,color:C.headDark,marginBottom:10,lineHeight:1.05}}>{a.name}</h3>
              <p style={{fontSize:12,color:C.gray,lineHeight:1.6,fontWeight:300}}>{a.desc}</p>
            </div>
          ))}
        </div>
      </Reveal>
    </section>
  );
}

// ─── EXAMPLES ─────────────────────────────────────────────────────────────────
function Examples(){
  const [filter,setFilter]=useState("all");
  const filters=["all","Курсовая","Реферат","ВКР","Эссе"];
  const filtered=filter==="all"?EXAMPLES:EXAMPLES.filter(e=>e.type===filter);
  return(
    <section id="examples" style={{background:C.offwhite,padding:"80px 32px",borderBottom:`1px solid ${C.black}`}}>
      <Reveal style={{maxWidth:1100,margin:"0 auto"}}>
        <Tag>ПРИМЕРЫ</Tag>
        <h2 className="H" style={{fontSize:"clamp(40px,6vw,72px)",marginBottom:12,lineHeight:0.92}}><span style={{color:C.headGray}}>ПРИМЕРЫ</span><br/><span style={{color:C.black}}>РАБОТ</span></h2>
        <div style={{display:"inline-flex",alignItems:"center",gap:8,padding:"7px 14px",border:`1px solid ${C.border}`,marginBottom:20}}>
          <div style={{width:6,height:6,borderRadius:"50%",background:C.grayMid,flexShrink:0}}/>
          <span style={{fontSize:11,color:C.gray,fontWeight:300}}>Демонстрационные работы — ваши работы автоматически удаляются в течение 24 часов</span>
        </div>
        <HR style={{marginBottom:14}}/>
        <div style={{display:"flex",gap:0,flexWrap:"wrap",marginBottom:20,border:`1px solid ${C.border}`}}>
          {filters.map((f,i)=>(
            <button key={f} onClick={()=>setFilter(f)}
              style={{padding:"10px 20px",border:"none",borderRight:i<filters.length-1?`1px solid ${C.border}`:"none",background:filter===f?C.black:"transparent",color:filter===f?"#fff":C.gray,fontFamily:"'Barlow Condensed',sans-serif",fontWeight:700,fontSize:12,textTransform:"uppercase",letterSpacing:"0.1em",cursor:"pointer",transition:"all 0.15s"}}>
              {f==="all"?"ВСЕ":f}
            </button>
          ))}
        </div>
        <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fill,minmax(270px,1fr))",gap:1,background:C.black}}>
          {filtered.map((ex,i)=>(
            <div key={i} style={{background:"#fff",padding:22,transition:"background 0.15s",cursor:"default"}}
              onMouseEnter={e=>e.currentTarget.style.background=C.offwhite}
              onMouseLeave={e=>e.currentTarget.style.background="#fff"}>
              <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:12}}>
                <span className="LBL" style={{fontSize:10,color:C.gray}}>{ex.type}</span>
                <span className="LBL" style={{fontSize:10,color:C.grayMid}}>{ex.pages} СТР.</span>
              </div>
              <h4 style={{fontFamily:"'Barlow Condensed',sans-serif",fontWeight:700,fontSize:17,letterSpacing:"-0.01em",marginBottom:6,lineHeight:1.2,textTransform:"uppercase"}}>{ex.topic}</h4>
              <div className="LBL" style={{fontSize:10,color:C.grayMid,marginBottom:16}}>{ex.subject}</div>
              <div>
                <div style={{display:"flex",justifyContent:"space-between",marginBottom:5}}>
                  <span className="LBL" style={{fontSize:10,color:C.gray}}>УНИКАЛЬНОСТЬ</span>
                  <span className="H" style={{fontSize:16,color:C.headDark}}>{ex.unique}%</span>
                </div>
                <div style={{height:2,background:C.border}}>
                  <div style={{height:"100%",width:`${ex.unique}%`,background:C.black,transition:"width 1s ease"}}/>
                </div>
              </div>
              <button style={{marginTop:14,width:"100%",padding:"9px",border:`1px solid ${C.border}`,background:"transparent",color:C.gray,fontFamily:"'Barlow Condensed',sans-serif",fontWeight:600,fontSize:12,textTransform:"uppercase",letterSpacing:"0.08em",cursor:"pointer",display:"flex",alignItems:"center",justifyContent:"center",gap:5,transition:"all 0.15s"}}
                onMouseEnter={e=>{e.currentTarget.style.background=C.black;e.currentTarget.style.color="#fff";e.currentTarget.style.borderColor=C.black;}}
                onMouseLeave={e=>{e.currentTarget.style.background="transparent";e.currentTarget.style.color=C.gray;e.currentTarget.style.borderColor=C.border;}}>
                <Download size={11}/> СКАЧАТЬ PDF
              </button>
            </div>
          ))}
        </div>
      </Reveal>
    </section>
  );
}

// ─── PRICING ──────────────────────────────────────────────────────────────────
function Pricing({onOrder}){
  const [sel,setSel]=useState("course");
  const cur=WORK_TYPES.find(w=>w.id===sel);
  const total=cur?.price||0;

  return(
    <section id="prices" style={{background:"#fff",padding:"80px 32px",borderBottom:`1px solid ${C.black}`}}>
      <Reveal style={{maxWidth:960,margin:"0 auto"}}>
        <Tag>ЦЕНЫ</Tag>
        <h2 className="H" style={{fontSize:"clamp(40px,6vw,72px)",marginBottom:8,lineHeight:0.92}}><span style={{color:C.headGray}}>ПРОЗРАЧНЫЕ ЦЕНЫ</span><br/><span style={{color:C.black}}>БЕЗ СКРЫТЫХ ДОПЛАТ</span></h2>
        <p style={{fontSize:13,color:C.gray,marginBottom:28,fontWeight:300}}>Без подписки — платишь за конкретную работу</p>
        <HR style={{marginBottom:0}}/>
        <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(300px,1fr))",gap:1,background:C.black}}>

          {/* Free */}
          <div style={{background:"#fff",padding:32}}>
            <div className="LBL" style={{color:C.gray,fontSize:10,marginBottom:14}}>БЕСПЛАТНО</div>
            <div className="H" style={{fontSize:64,color:C.headGray,marginBottom:24}}>0 ₽</div>
            {["Описание и цели работы","Задачи и структура","Актуальные данные","× Без экспорта полного текста"].map((f,i)=>(
              <div key={i} style={{display:"flex",alignItems:"flex-start",gap:10,padding:"10px 0",color:f.startsWith("×")?C.grayLight:C.black,fontSize:13,borderBottom:`1px solid ${C.border}`,fontWeight:300}}>
                <span style={{flexShrink:0,fontFamily:"'Barlow Condensed',sans-serif",fontWeight:700,fontSize:14}}>{f.startsWith("×")?"×":"+"}</span>
                {f.replace("× ","")}
              </div>
            ))}
            <button onClick={onOrder}
              style={{display:"block",marginTop:24,padding:"13px",border:`1px solid ${C.black}`,color:C.black,background:"#fff",fontFamily:"'Barlow Condensed',sans-serif",fontWeight:700,fontSize:13,textTransform:"uppercase",letterSpacing:"0.12em",textAlign:"center",cursor:"pointer",width:"100%",transition:"all 0.15s"}}
              onMouseEnter={e=>{e.currentTarget.style.background=C.black;e.currentTarget.style.color="#fff";}}
              onMouseLeave={e=>{e.currentTarget.style.background="#fff";e.currentTarget.style.color=C.black;}}>
              ПОПРОБОВАТЬ БЕСПЛАТНО
            </button>
          </div>

          {/* Paid */}
          <div style={{background:C.offwhite,padding:32,position:"relative"}}>
            <div style={{position:"absolute",top:0,left:0,right:0}}>
              <div className="LBL" style={{background:C.black,color:"#fff",textAlign:"center",padding:"6px",fontSize:10,letterSpacing:"0.2em"}}>
                ПОПУЛЯРНЫЙ
              </div>
            </div>
            <div style={{marginTop:32}}>
              <div className="LBL" style={{color:C.gray,fontSize:10,marginBottom:14}}>РАСШИРЕННАЯ ВЕРСИЯ</div>
              <select value={sel} onChange={e=>setSel(e.target.value)}
                style={{width:"100%",padding:"10px 12px",border:`1px solid ${C.border}`,background:"#fff",color:C.black,fontSize:13,cursor:"pointer",marginBottom:10,outline:"none"}}>
                {WORK_TYPES.map(w=><option key={w.id} value={w.id}>{w.label} — {w.pages} стр.</option>)}
              </select>
              <div className="H" style={{fontSize:64,color:C.black,marginBottom:4}}>
                {total} <span style={{fontSize:28,fontWeight:300}}>₽</span>
              </div>
            </div>
            {["Полный текст "+(cur?.pages||"")+" стр.","Экспорт Word","Уникальность 85–95%","Проверка антиплагиата","Таблицы + графики по ГОСТу"].map((f,i)=>(
              <div key={i} style={{display:"flex",alignItems:"flex-start",gap:10,padding:"10px 0",color:C.black,fontSize:13,borderBottom:`1px solid ${C.border}`,fontWeight:300}}>
                <span style={{flexShrink:0,fontFamily:"'Barlow Condensed',sans-serif",fontWeight:700,fontSize:14}}>+</span>{f}
              </div>
            ))}
            <button onClick={onOrder}
              style={{display:"block",marginTop:24,padding:"13px",background:C.black,color:"#fff",border:"none",fontFamily:"'Barlow Condensed',sans-serif",fontWeight:700,fontSize:13,textTransform:"uppercase",letterSpacing:"0.12em",textAlign:"center",cursor:"pointer",width:"100%"}}>
              ЗАКАЗАТЬ ЗА {total}₽
            </button>
          </div>
        </div>
      </Reveal>
    </section>
  );
}

// ─── FAQ ──────────────────────────────────────────────────────────────────────
function FAQSection(){
  const [open,setOpen]=useState(null);
  return(
    <section id="faq" style={{background:C.offwhite,padding:"80px 32px",borderBottom:`1px solid ${C.black}`}}>
      <Reveal style={{maxWidth:760,margin:"0 auto"}}>
        <Tag>FAQ</Tag>
        <h2 className="H" style={{fontSize:"clamp(40px,6vw,72px)",marginBottom:28,lineHeight:0.92}}><span style={{color:C.headGray}}>ЧАСТЫЕ</span><br/><span style={{color:C.black}}>ВОПРОСЫ</span></h2>
        <HR style={{marginBottom:0}}/>
        {FAQ_ITEMS.map((item,i)=>(
          <div key={i} style={{borderBottom:`1px solid ${C.border}`}}>
            <button onClick={()=>setOpen(open===i?null:i)}
              style={{width:"100%",padding:"18px 0",background:"none",border:"none",cursor:"pointer",display:"flex",justifyContent:"space-between",alignItems:"center",textAlign:"left",gap:16}}>
              <span style={{fontFamily:"'Barlow Condensed',sans-serif",fontWeight:700,fontSize:16,color:C.black,flex:1,textTransform:"uppercase",letterSpacing:"0.02em",lineHeight:1.2}}>{item.q}</span>
              <ChevronDown size={15} color={C.gray} style={{transform:open===i?"rotate(180deg)":"rotate(0)",transition:"transform 0.25s",flexShrink:0}}/>
            </button>
            <div style={{maxHeight:open===i?300:0,overflow:"hidden",transition:"max-height 0.35s ease"}}>
              <p style={{padding:"0 0 18px",color:C.gray,lineHeight:1.7,fontSize:14,fontWeight:300}}>{item.a}</p>
            </div>
          </div>
        ))}
      </Reveal>
    </section>
  );
}

// ─── FINAL CTA ────────────────────────────────────────────────────────────────
function FinalCTA({onOrder}){
  return(
    <section id="cta" style={{background:C.black,padding:"100px 32px",position:"relative",overflow:"hidden"}}>
      {/* ghost watermark — just like big "VITAMIN WELL" behind label text */}
      <div className="H" style={{position:"absolute",top:"50%",left:"50%",transform:"translate(-50%,-50%)",fontSize:"20vw",color:"rgba(255,255,255,0.04)",whiteSpace:"nowrap",pointerEvents:"none",userSelect:"none",letterSpacing:"-0.02em"}}>
        REFERAT
      </div>
      <Reveal style={{position:"relative",zIndex:1,maxWidth:900,margin:"0 auto"}}>
        <div className="LBL" style={{color:"rgba(255,255,255,0.35)",marginBottom:16,fontSize:10}}>
          — НАЧНИ ПРЯМО СЕЙЧАС —
        </div>
        <h2 className="H" style={{fontSize:"clamp(60px,12vw,140px)",marginBottom:20,lineHeight:0.88}}>
          <span style={{color:"rgba(255,255,255,0.45)"}}>ПОПРОБУЙ</span><br/><span style={{color:"#fff"}}>БЕСПЛАТНО</span>
        </h2>
        <div style={{display:"flex",alignItems:"center",gap:0,marginBottom:36}}>
          <div style={{height:1,flex:1,background:"rgba(255,255,255,0.1)"}}/>
          <span className="LBL" style={{color:"rgba(255,255,255,0.35)",padding:"0 20px",fontSize:10}}>ПЕРВЫЙ ПЛАН БЕЗ РЕГИСТРАЦИИ</span>
          <div style={{height:1,flex:1,background:"rgba(255,255,255,0.1)"}}/>
        </div>
        <div style={{display:"flex",gap:10,flexWrap:"wrap",alignItems:"center"}}>
          <button onClick={onOrder}
            style={{display:"inline-flex",alignItems:"center",gap:8,padding:"16px 40px",background:"#fff",color:C.black,fontFamily:"'Barlow Condensed',sans-serif",fontWeight:800,fontSize:15,textTransform:"uppercase",letterSpacing:"0.12em",border:"1px solid #fff",transition:"all 0.15s",cursor:"pointer"}}
            onMouseEnter={e=>{e.currentTarget.style.background="transparent";e.currentTarget.style.color="#fff";}}
            onMouseLeave={e=>{e.currentTarget.style.background="#fff";e.currentTarget.style.color=C.black;}}>
            НАЧАТЬ БЕСПЛАТНО <ArrowRight size={15}/>
          </button>
          <span className="LBL" style={{color:"rgba(255,255,255,0.3)",fontSize:10}}>ПЛАН — БЕСПЛАТНО</span>
        </div>
      </Reveal>
    </section>
  );
}

// ─── FOOTER ───────────────────────────────────────────────────────────────────
function Footer({onOferta,onPrivacy}){
  return(
    <footer style={{background:C.offwhite,padding:"52px 32px 28px",borderTop:`1px solid ${C.black}`}}>
      <div style={{maxWidth:1100,margin:"0 auto"}}>
        <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(170px,1fr))",gap:40,marginBottom:40}}>
          <div>
            <div className="H" style={{fontSize:20,marginBottom:12,color:C.headDark}}>REFERAT<span style={{fontWeight:300,color:C.black}}>.IO</span></div>
            <p style={{color:C.gray,fontSize:13,lineHeight:1.65,fontWeight:300,marginBottom:14}}>Академические работы с уникальностью 85–95%</p>
          </div>
          <div>
            <div className="LBL" style={{color:C.black,fontSize:10,marginBottom:14}}>О СЕРВИСЕ</div>
            {["Цены","FAQ","Отзывы"].map(l=>(
              <div key={l} style={{marginBottom:8}}>
                <a href="#" style={{color:C.gray,fontSize:13,textDecoration:"none",fontWeight:300}}
                  onMouseEnter={e=>e.target.style.color=C.black}
                  onMouseLeave={e=>e.target.style.color=C.gray}>{l}</a>
              </div>
            ))}
          </div>
          <div>
            <div className="LBL" style={{color:C.black,fontSize:10,marginBottom:14}}>ИНФОРМАЦИЯ</div>
            <div style={{marginBottom:8}}>
              <button onClick={onOferta} style={{background:"none",border:"none",padding:0,color:C.gray,fontSize:13,textDecoration:"none",fontWeight:300,cursor:"pointer"}}
                onMouseEnter={e=>e.target.style.color=C.black}
                onMouseLeave={e=>e.target.style.color=C.gray}>Публичная оферта</button>
            </div>
            <div style={{marginBottom:8}}>
              <button onClick={onPrivacy} style={{background:"none",border:"none",padding:0,color:C.gray,fontSize:13,textDecoration:"none",fontWeight:300,cursor:"pointer"}}
                onMouseEnter={e=>e.target.style.color=C.black}
                onMouseLeave={e=>e.target.style.color=C.gray}>Политика конфиденциальности</button>
            </div>
          </div>
          <div>
            <div className="LBL" style={{color:C.black,fontSize:10,marginBottom:14}}>ПОДДЕРЖКА</div>
            {["Telegram","Онлайн-чат"].map(l=>(
              <div key={l} style={{marginBottom:8}}>
                <a href="#" style={{color:C.gray,fontSize:13,textDecoration:"none",fontWeight:300}}
                  onMouseEnter={e=>e.target.style.color=C.black}
                  onMouseLeave={e=>e.target.style.color=C.gray}>{l}</a>
              </div>
            ))}
          </div>
        </div>
        <HR/>
        <div style={{paddingTop:18,display:"flex",justifyContent:"space-between",alignItems:"center",flexWrap:"wrap",gap:10}}>
          <span className="LBL" style={{color:C.grayMid,fontSize:9}}>© 2025–2026 ИП Карпов Даниил Юрьевич · ИНН 772515432577 · ОГРНИП 325508100131425</span>
          <div style={{display:"flex",gap:20}}>
            {[["IRecommend","4.9"],["Яндекс","4.9"],["Отзовик","5.0"]].map(([p,r])=>(
              <span key={p} className="LBL" style={{color:C.grayMid,fontSize:9}}>{p}: <strong style={{color:C.black}}>{r}★</strong></span>
            ))}
          </div>
        </div>
      </div>
    </footer>
  );
}

// ─── MODAL SHELL ──────────────────────────────────────────────────────────────
function ModalShell({onClose,children,wide}){
  useEffect(()=>{
    document.body.style.overflow="hidden";
    return()=>{document.body.style.overflow="";};
  },[]);
  return(
    <div onClick={onClose} style={{position:"fixed",inset:0,background:"rgba(0,0,0,0.6)",zIndex:1000,display:"flex",alignItems:"center",justifyContent:"center",padding:"16px",backdropFilter:"blur(2px)"}}>
      <div onClick={e=>e.stopPropagation()} style={{background:"#fff",border:`1px solid ${C.black}`,width:"100%",maxWidth:wide?820:600,maxHeight:"90vh",display:"flex",flexDirection:"column",boxShadow:"0 24px 64px rgba(0,0,0,0.18)"}}>
        {children}
      </div>
    </div>
  );
}

// ─── ORDER MODAL ──────────────────────────────────────────────────────────────
const PLAN_TEMPLATE = (topic, dir) => {
  const d = DIRECTIONS.find(x=>x.code===dir)||DIRECTIONS[0];
  return `КУРСОВАЯ РАБОТА

Тема: ${topic}
Направление: ${d.code} ${d.label}

СОДЕРЖАНИЕ

Введение ............................................................ 3
  — Актуальность. Степень научной разработанности темы.
  — Цель, задачи, объект, предмет исследования.
  — Методологическая база. Структура работы.

Глава 1. Теоретико-методологические основы исследования
  §1.1. Основные понятия и концептуальный аппарат ..................... 7
  §1.2. Современные подходы и научные дискуссии в литературе .......... 12

Глава 2. Анализ предметной области
  §2.1. Нормативно-правовая база и институциональный контекст ......... 18
  §2.2. Эмпирический анализ: данные и методика исследования ........... 23
  §2.3. Результаты и интерпретация полученных данных .................. 29

Глава 3. Проблемы и перспективы
  §3.1. Выявленные противоречия и ограничения ........................ 35
  §3.2. Направления совершенствования на основе анализа источников ... 40

Заключение .......................................................... 46
Список использованных источников и литературы (26 источников) ........ 49
  — Нормативно-правовые акты: 4 источника
  — Монографии и научные статьи: 16 источников (2019–2024)
  — Статистические материалы: 6 источников`;
};

function OrderModal({onClose, prefill={}}){
  const [step,setStep]=useState(prefill.topic ? 2 : 1);
  const [workType,setWorkType]=useState(prefill.workType||"course");
  const [direction,setDirection]=useState(prefill.direction||"38.03.01");
  const [topic,setTopic]=useState(prefill.topic||"");
  const [plan,setPlan]=useState(prefill.topic ? PLAN_TEMPLATE(prefill.topic, prefill.direction||"38.03.01") : "");
  const [generating,setGenerating]=useState(prefill.topic ? false : false);
  const [email,setEmail]=useState("");
  const [agree,setAgree]=useState(false);
  const [copied,setCopied]=useState(false);
  const planRef=useRef(null);

  const cur = WORK_TYPES.find(w=>w.id===workType)||WORK_TYPES[0];

  const generate=()=>{
    if(!topic.trim()) return;
    setGenerating(true);
    setTimeout(()=>{
      setPlan(PLAN_TEMPLATE(topic, direction));
      setGenerating(false);
      setStep(2);
    },1800);
  };

  const copyPlan=()=>{
    navigator.clipboard?.writeText(plan).then(()=>{setCopied(true);setTimeout(()=>setCopied(false),2000);});
  };

  const SBP_AMOUNT = cur.price;

  const STEPS = ["ПАРАМЕТРЫ","ПЛАН","ОПЛАТА"];

  return(
    <ModalShell onClose={onClose} wide>
      {/* Header */}
      <div style={{background:C.black,padding:"14px 24px",display:"flex",justifyContent:"space-between",alignItems:"center",flexShrink:0}}>
        <div style={{display:"flex",alignItems:"center",gap:24}}>
          <span className="H" style={{color:"#fff",fontSize:18}}>ГЕНЕРАЦИЯ РАБОТЫ</span>
          <div style={{display:"flex",gap:0}}>
            {STEPS.map((s,i)=>(
              <div key={i} style={{display:"flex",alignItems:"center",gap:6}}>
                <div style={{display:"flex",alignItems:"center",gap:6,opacity:step===i+1?1:0.4}}>
                  <div style={{width:18,height:18,borderRadius:"50%",background:step>i+1?"#4ade80":step===i+1?"#fff":"transparent",border:"1.5px solid",borderColor:step>i+1?"#4ade80":"rgba(255,255,255,0.5)",display:"flex",alignItems:"center",justifyContent:"center"}}>
                    {step>i+1
                      ?<span style={{fontSize:10,color:C.black,fontWeight:700}}>✓</span>
                      :<span style={{fontSize:10,color:step===i+1?C.black:"rgba(255,255,255,0.5)",fontWeight:700}}>{i+1}</span>}
                  </div>
                  <span className="LBL" style={{color:"rgba(255,255,255,0.8)",fontSize:9}}>{s}</span>
                </div>
                {i<2&&<div style={{width:20,height:1,background:"rgba(255,255,255,0.2)",margin:"0 4px"}}/>}
              </div>
            ))}
          </div>
        </div>
        <button onClick={onClose} style={{background:"none",border:"none",cursor:"pointer",color:"rgba(255,255,255,0.6)",padding:4,display:"flex"}}><Close size={18}/></button>
      </div>

      {/* Body */}
      <div style={{flex:1,overflowY:"auto",padding:"28px 28px 0"}}>

        {/* STEP 1 — FORM */}
        {step===1&&(
          <div style={{display:"flex",flexDirection:"column",gap:14}}>
            <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:10}}>
              <div>
                <div className="LBL" style={{fontSize:9,color:C.gray,marginBottom:5}}>ТИП РАБОТЫ</div>
                <select value={workType} onChange={e=>setWorkType(e.target.value)}
                  style={{width:"100%",padding:"10px 12px",border:`1px solid ${C.border}`,background:C.offwhite,color:C.black,fontSize:13,cursor:"pointer",outline:"none"}}>
                  {WORK_TYPES.map(w=><option key={w.id} value={w.id}>{w.label} — {w.pages} стр.</option>)}
                </select>
              </div>
              <div>
                <div className="LBL" style={{fontSize:9,color:C.gray,marginBottom:5}}>НАПРАВЛЕНИЕ ПОДГОТОВКИ</div>
                <select value={direction} onChange={e=>setDirection(e.target.value)}
                  style={{width:"100%",padding:"10px 12px",border:`1px solid ${C.border}`,background:C.offwhite,color:C.black,fontSize:13,cursor:"pointer",outline:"none"}}>
                  {DIRECTIONS.map(d=><option key={d.code} value={d.code}>{d.code} · {d.label}</option>)}
                </select>
              </div>
            </div>
            <div>
              <div className="LBL" style={{fontSize:9,color:C.gray,marginBottom:5}}>ТЕМА РАБОТЫ</div>
              <textarea value={topic} onChange={e=>setTopic(e.target.value)}
                placeholder="Введите точную тему вашей работы..."
                rows={3}
                style={{width:"100%",padding:"10px 12px",border:`1px solid ${topic.trim()?C.black:C.border}`,background:C.offwhite,color:C.black,fontSize:13,outline:"none",resize:"vertical",fontFamily:"'Barlow',sans-serif",lineHeight:1.5}}/>
            </div>
          </div>
        )}

        {/* STEP 2 — PLAN */}
        {step===2&&(
          <div style={{display:"flex",flexDirection:"column",gap:12}}>
            <div style={{display:"flex",justifyContent:"space-between",alignItems:"center"}}>
              <span className="LBL" style={{fontSize:9,color:C.gray}}>СГЕНЕРИРОВАННЫЙ ПЛАН — МОЖНО РЕДАКТИРОВАТЬ</span>
              <button onClick={copyPlan}
                style={{padding:"5px 12px",border:`1px solid ${C.border}`,background:"transparent",color:C.gray,fontFamily:"'Barlow Condensed',sans-serif",fontWeight:600,fontSize:11,textTransform:"uppercase",letterSpacing:"0.08em",cursor:"pointer"}}>
                {copied?"СКОПИРОВАНО ✓":"КОПИРОВАТЬ"}
              </button>
            </div>
            <textarea ref={planRef} value={plan} onChange={e=>setPlan(e.target.value)}
              style={{width:"100%",padding:"16px",border:`1px solid ${C.border}`,background:C.offwhite,color:C.black,fontSize:12,outline:"none",resize:"vertical",fontFamily:"monospace",lineHeight:1.7,minHeight:300}}/>
            <div style={{background:"#F0F7F0",border:"1px solid #C6E8D4",padding:"10px 14px",fontSize:12,color:"#3a7a4a"}}>
              ✓ Уникальность: 85–95% · ГОСТ Р 7.0.100-2018 · Без плашки «подозрительный текст»
            </div>
            <div style={{background:C.offwhite,padding:"12px 16px",border:`1px solid ${C.border}`,display:"flex",justifyContent:"space-between",alignItems:"center"}}>
              <span style={{fontSize:13,color:C.gray,fontWeight:300}}>Стоимость работы</span>
              <span className="H" style={{fontSize:28,color:C.black}}>{cur.price} <span style={{fontSize:16,fontWeight:300}}>₽</span></span>
            </div>
          </div>
        )}

        {/* STEP 3 — PAY */}
        {step===3&&(
          <div style={{display:"flex",flexDirection:"column",gap:14}}>
            <div>
              <div className="LBL" style={{fontSize:9,color:C.gray,marginBottom:5}}>EMAIL ДЛЯ ПОЛУЧЕНИЯ РАБОТЫ</div>
              <input value={email} onChange={e=>setEmail(e.target.value)} type="email"
                placeholder="your@email.ru"
                style={{width:"100%",padding:"12px 14px",border:`1px solid ${email.includes("@")?C.black:C.border}`,background:C.offwhite,color:C.black,fontSize:14,outline:"none",fontFamily:"'Barlow',sans-serif"}}/>
              <div style={{fontSize:11,color:C.grayMid,marginTop:5,fontWeight:300}}>Готовая работа придёт на этот адрес в течение 10 минут после оплаты</div>
            </div>

            {/* Order summary */}
            <div style={{border:`1px solid ${C.border}`}}>
              <div style={{background:C.offwhite,padding:"10px 16px",borderBottom:`1px solid ${C.border}`}}>
                <span className="LBL" style={{fontSize:9,color:C.gray}}>СОСТАВ ЗАКАЗА</span>
              </div>
              {[
                ["Тип работы", cur.label],
                ["Объём", cur.pages+" стр."],
                ["Направление", (DIRECTIONS.find(d=>d.code===direction)||DIRECTIONS[0]).label],
                ["Тема", topic],
                ["Оформление", "ГОСТ Р 7.0.100-2018"],
                ["Уникальность", "85–95%"],
              ].map(([k,v])=>(
                <div key={k} style={{display:"flex",justifyContent:"space-between",padding:"9px 16px",borderBottom:`1px solid ${C.border}`,gap:16}}>
                  <span style={{fontSize:12,color:C.grayMid,fontWeight:300,flexShrink:0}}>{k}</span>
                  <span style={{fontSize:12,color:C.black,textAlign:"right"}}>{v}</span>
                </div>
              ))}
              <div style={{display:"flex",justifyContent:"space-between",padding:"14px 16px",background:C.black}}>
                <span className="LBL" style={{fontSize:10,color:"rgba(255,255,255,0.6)"}}>ИТОГО</span>
                <span className="H" style={{fontSize:26,color:"#fff"}}>{cur.price} ₽</span>
              </div>
            </div>

            {/* Agree */}
            <label style={{display:"flex",alignItems:"flex-start",gap:10,cursor:"pointer",userSelect:"none"}}>
              <div onClick={()=>setAgree(!agree)}
                style={{width:16,height:16,border:`2px solid ${agree?C.black:C.border}`,background:agree?C.black:"transparent",flexShrink:0,marginTop:1,display:"flex",alignItems:"center",justifyContent:"center",cursor:"pointer"}}>
                {agree&&<span style={{color:"#fff",fontSize:10,lineHeight:1}}>✓</span>}
              </div>
              <span style={{fontSize:12,color:C.gray,fontWeight:300,lineHeight:1.5}}>
                Я принимаю условия <button onClick={(e)=>{e.preventDefault();window.__openOferta&&window.__openOferta();}} style={{background:"none",border:"none",padding:0,color:C.black,textDecoration:"underline",cursor:"pointer",fontSize:12,fontFamily:"'Barlow',sans-serif"}}>публичной оферты</button> и <button onClick={(e)=>{e.preventDefault();window.__openPrivacy&&window.__openPrivacy();}} style={{background:"none",border:"none",padding:0,color:C.black,textDecoration:"underline",cursor:"pointer",fontSize:12,fontFamily:"'Barlow',sans-serif"}}>политики конфиденциальности</button>
              </span>
            </label>
          </div>
        )}
      </div>

      {/* Footer buttons */}
      <div style={{padding:"20px 28px",borderTop:`1px solid ${C.border}`,display:"flex",gap:10,flexShrink:0,background:"#fff"}}>
        {step===1&&(
          <>
            <button onClick={onClose}
              style={{padding:"12px 24px",border:`1px solid ${C.border}`,background:"transparent",color:C.gray,fontFamily:"'Barlow Condensed',sans-serif",fontWeight:700,fontSize:13,textTransform:"uppercase",letterSpacing:"0.1em",cursor:"pointer"}}>
              ОТМЕНА
            </button>
            <button onClick={generate} disabled={!topic.trim()||generating}
              style={{flex:1,padding:"13px",background:topic.trim()&&!generating?C.black:C.offwhite,border:`1px solid ${topic.trim()&&!generating?C.black:C.border}`,color:topic.trim()&&!generating?"#fff":C.grayMid,fontFamily:"'Barlow Condensed',sans-serif",fontWeight:700,fontSize:14,textTransform:"uppercase",letterSpacing:"0.12em",cursor:topic.trim()&&!generating?"pointer":"default",transition:"all 0.15s",display:"flex",alignItems:"center",justifyContent:"center",gap:8}}>
              {generating
                ?<><div style={{width:13,height:13,border:`1.5px solid ${C.grayMid}`,borderTopColor:"transparent",borderRadius:"50%",animation:"spin 0.7s linear infinite"}}/> ГЕНЕРИРУЮ ПЛАН...</>
                :"СГЕНЕРИРОВАТЬ ПЛАН →"}
            </button>
          </>
        )}
        {step===2&&(
          <>
            <button onClick={()=>setStep(1)}
              style={{padding:"12px 24px",border:`1px solid ${C.border}`,background:"transparent",color:C.gray,fontFamily:"'Barlow Condensed',sans-serif",fontWeight:700,fontSize:13,textTransform:"uppercase",letterSpacing:"0.1em",cursor:"pointer"}}>
              ← НАЗАД
            </button>
            <button onClick={()=>setStep(3)}
              style={{flex:1,padding:"13px",background:C.black,border:`1px solid ${C.black}`,color:"#fff",fontFamily:"'Barlow Condensed',sans-serif",fontWeight:700,fontSize:14,textTransform:"uppercase",letterSpacing:"0.12em",cursor:"pointer",transition:"all 0.15s"}}>
              УТВЕРЖДАЮ ПЛАН → ПЕРЕЙТИ К ОПЛАТЕ
            </button>
          </>
        )}
        {step===3&&(
          <>
            <button onClick={()=>setStep(2)}
              style={{padding:"12px 24px",border:`1px solid ${C.border}`,background:"transparent",color:C.gray,fontFamily:"'Barlow Condensed',sans-serif",fontWeight:700,fontSize:13,textTransform:"uppercase",letterSpacing:"0.1em",cursor:"pointer"}}>
              ← НАЗАД
            </button>
            <button
              disabled={!email.includes("@")||!agree}
              style={{flex:1,padding:"13px",background:email.includes("@")&&agree?"#1A9E4A":C.offwhite,border:"none",color:email.includes("@")&&agree?"#fff":C.grayMid,fontFamily:"'Barlow Condensed',sans-serif",fontWeight:800,fontSize:15,textTransform:"uppercase",letterSpacing:"0.1em",cursor:email.includes("@")&&agree?"pointer":"default",transition:"all 0.2s",display:"flex",alignItems:"center",justifyContent:"center",gap:10}}>
              <span style={{fontSize:20}}>⊕</span>
              ОПЛАТИТЬ {cur.price} ₽ ЧЕРЕЗ СБП
            </button>
          </>
        )}
      </div>
    </ModalShell>
  );
}

// ─── OFERTA MODAL ─────────────────────────────────────────────────────────────
function OfertaModal({onClose}){
  return(
    <ModalShell onClose={onClose} wide>
      <div style={{background:C.black,padding:"14px 24px",display:"flex",justifyContent:"space-between",alignItems:"center",flexShrink:0}}>
        <span className="H" style={{color:"#fff",fontSize:18}}>ПУБЛИЧНАЯ ОФЕРТА</span>
        <button onClick={onClose} style={{background:"none",border:"none",cursor:"pointer",color:"rgba(255,255,255,0.6)",padding:4,display:"flex"}}><Close size={18}/></button>
      </div>
      <div style={{flex:1,overflowY:"auto",padding:"32px 36px",fontSize:13,color:C.black,lineHeight:1.8,fontWeight:300}}>
        <p style={{marginBottom:20,color:C.gray}}>Настоящая оферта является предложением ИП Карпов Даниил Юрьевич, ИНН 772515432577, ОГРНИП 325508100131425 (далее — Исполнитель) заключить договор на оказание информационных услуг онлайн-сервиса «referat.io», размещённого в интернете по адресу https://referat.io/</p>

        {[
          ["1. Определения",`1.1. Оферта — текст настоящего документа со всеми приложениями, изменениями и дополнениями, размещённый на сайте Исполнителя по адресу https://referat.io/oferta/.

1.2. Договор — договор оказания возмездных услуг, заключаемый и исполняемый Сторонами в порядке, предусмотренном настоящей Офертой.

1.3. Услуги — информационные услуги по генерации академических текстовых материалов с использованием технологий искусственного интеллекта и предоставлению доступа к сгенерированным материалам в формате документа Microsoft Word (DOCX).

1.4. Исполнитель — ИП Карпов Даниил Юрьевич, ИНН 772515432577, ОГРНИП 325508100131425.

1.5. Заказчик — физическое лицо, совершившее акцепт настоящей Оферты в порядке, предусмотренном разделом 6.

1.6. Заказ — действия Заказчика по выбору параметров и оплате услуг, необходимых для генерации конкретного документа.

1.7. Сервис — программный комплекс referat.io, доступный по адресу https://app.referat.io, обеспечивающий генерацию академических текстов.`],

          ["2. Предмет договора",`2.1. Исполнитель обязуется при наличии технической возможности оказывать Услуги на основании оформленных Заказов, а Заказчик — принимать и оплачивать Услуги на условиях настоящей Оферты.

2.2. Состав, объём и стоимость Услуг определяются параметрами Заказа, указанными Заказчиком при его оформлении.

2.3. Обязательным условием оказания Услуг является принятие Заказчиком Политики конфиденциальности, размещённой по адресу https://referat.io/privacy/.

2.4. Услуги оказываются Заказчикам, достигшим возраста 18 лет. Использование сервиса лицом младше 18 лет допустимо исключительно с ведома и согласия законного представителя.

2.5. Регистрация, оформление заказа или оплата означает полное и безусловное принятие условий настоящей Оферты.`],

          ["3. Стоимость услуг и порядок расчётов",`3.1. Стоимость Услуг определяется в соответствии с ценами, указанными на странице оформления заказа, и зависит от выбранного типа работы.

3.2. Оплата Услуг производится в российских рублях посредством сервиса Системы быстрых платежей (СБП) Банка России.

3.3. Стоимость услуг не облагается НДС в соответствии с п. 2 ст. 346.11 Налогового кодекса Российской Федерации.

3.4. Услуги оказываются на условиях 100% предварительной оплаты. Внесение оплаты является фактом акцепта настоящей Оферты.`],

          ["4. Гарантии и ответственность",`4.1. Исполнитель гарантирует предоставление сгенерированного текста в формате Microsoft Word (DOCX) на электронную почту Заказчика в течение 10 минут после подтверждения оплаты.

4.2. Исполнитель предпримет все усилия для устранения сбоев и ошибок. При этом Исполнитель не гарантирует отсутствия технических сбоев в работе сторонних сервисов.

4.3. Исполнитель не несёт ответственности за косвенные убытки и упущенную выгоду Заказчика.

4.4. Стороны освобождаются от ответственности за неисполнение обязательств вследствие обстоятельств непреодолимой силы.

4.5. Использование Сервиса для создания контента, нарушающего законодательство РФ, разжигающего ненависть, дискриминирующего по любому признаку, содержащего угрозы, а также для академических нарушений, запрещено. Исполнитель вправе отказать в оказании услуг при выявлении нарушений.`],

          ["5. Порядок возврата денежных средств",`Возврат средств возможен в случаях:

— Файл заказа недоступен через 6 часов после оплаты;
— Файл не открывается в Microsoft Word;
— Текст работы не читаем или полностью отсутствует;
— Текст полностью повторяется от главы к главе.

Срок возврата: 1–5 рабочих дней. Во всех остальных случаях услуга по генерации текста считается оказанной.

Для возврата Заказчик обращается в течение 10 календарных дней с момента покупки на адрес: support@referat.io, с описанием ситуации и прикреплёнными скриншотами.`],

          ["6. Акцепт оферты",`6.1. Оферта вступает в силу с момента размещения на сайте и действует до её отзыва Исполнителем.

6.2. Акцепт Оферты производится Заказчиком путём оплаты Заказа.

6.3. Датой акцепта считается дата поступления денежных средств Исполнителю.

6.4. Исполнитель вправе вносить изменения в Оферту в любой момент. Изменения вступают в силу с момента их публикации на сайте.`],

          ["7. Заключительные положения",`7.1. Все споры Стороны стремятся урегулировать путём переговоров. Срок ответа на претензию — 10 рабочих дней.

7.2. К отношениям Сторон применяется законодательство Российской Федерации.

7.3. Контактный адрес Исполнителя: support@referat.io`],

          ["8. Реквизиты исполнителя",`ИП Карпов Даниил Юрьевич
ИНН: 772515432577
ОГРНИП: 325508100131425

Адрес оферты: https://referat.io/oferta/

Редакция от 01.01.2026`],
        ].map(([title,text])=>(
          <div key={title} style={{marginBottom:28}}>
            <div className="LBL" style={{fontSize:10,color:C.black,marginBottom:10,borderBottom:`1px solid ${C.border}`,paddingBottom:8}}>{title}</div>
            <div style={{whiteSpace:"pre-wrap",color:C.gray}}>{text}</div>
          </div>
        ))}
      </div>
      <div style={{padding:"16px 28px",borderTop:`1px solid ${C.border}`,flexShrink:0}}>
        <button onClick={onClose}
          style={{width:"100%",padding:"12px",background:C.black,border:"none",color:"#fff",fontFamily:"'Barlow Condensed',sans-serif",fontWeight:700,fontSize:13,textTransform:"uppercase",letterSpacing:"0.12em",cursor:"pointer"}}>
          ЗАКРЫТЬ
        </button>
      </div>
    </ModalShell>
  );
}

// ─── PRIVACY MODAL ────────────────────────────────────────────────────────────
function PrivacyModal({onClose}){
  return(
    <ModalShell onClose={onClose} wide>
      <div style={{background:C.black,padding:"14px 24px",display:"flex",justifyContent:"space-between",alignItems:"center",flexShrink:0}}>
        <span className="H" style={{color:"#fff",fontSize:18}}>ПОЛИТИКА КОНФИДЕНЦИАЛЬНОСТИ</span>
        <button onClick={onClose} style={{background:"none",border:"none",cursor:"pointer",color:"rgba(255,255,255,0.6)",padding:4,display:"flex"}}><Close size={18}/></button>
      </div>
      <div style={{flex:1,overflowY:"auto",padding:"32px 36px",fontSize:13,color:C.black,lineHeight:1.8,fontWeight:300}}>
        <p style={{marginBottom:20,color:C.gray}}>Настоящая Политика конфиденциальности определяет порядок обработки персональных данных ИП Карпов Даниил Юрьевич (ИНН 772515432577, ОГРНИП 325508100131425) при использовании сервиса referat.io.</p>

        {[
          ["1. Оператор персональных данных",`ИП Карпов Даниил Юрьевич, ИНН 772515432577, ОГРНИП 325508100131425.
Контакт по вопросам персональных данных: support@referat.io`],

          ["2. Какие данные мы собираем",`При оформлении заказа:
— Адрес электронной почты (email) — для доставки готовой работы и уведомлений о заказе.

Автоматически при использовании сайта:
— IP-адрес, тип браузера, данные об устройстве — для обеспечения безопасности и корректной работы сервиса;
— Файлы cookie — для технической работы сайта и аналитики (подробнее — в разделе 6).

Данные, предоставленные добровольно:
— Параметры заказа (тема работы, направление подготовки) — исключительно для генерации заказанного документа.`],

          ["3. Цели обработки данных",`3.1. Исполнение договора: доставка заказанной работы на email, уведомления о статусе заказа.
3.2. Безопасность: предотвращение мошенничества и несанкционированного доступа.
3.3. Улучшение сервиса: анализ обезличенной статистики использования.
3.4. Маркетинговые рассылки — только при наличии явного согласия. От рассылки можно отписаться в любой момент.`],

          ["4. Правовое основание обработки",`Обработка персональных данных осуществляется на основании:
— согласия субъекта персональных данных (ст. 6 ч. 1 п. 1 ФЗ-152);
— исполнения договора (ст. 6 ч. 1 п. 5 ФЗ-152);
— законных интересов оператора (ст. 6 ч. 1 п. 7 ФЗ-152).`],

          ["5. Сроки хранения данных",`Email и параметры заказа хранятся в течение 3 лет с момента последней транзакции (требование налогового законодательства), после чего уничтожаются.
По запросу пользователя данные могут быть удалены досрочно, за исключением случаев, когда хранение обязательно по закону.`],

          ["6. Файлы cookie",`Мы используем:
— Технические cookie — необходимы для работы сайта;
— Аналитические cookie — для сбора обезличенной статистики (Яндекс.Метрика);
— Функциональные cookie — для сохранения предпочтений пользователя.
Вы можете отключить cookie в настройках браузера. Это может повлиять на функциональность сайта.`],

          ["7. Передача данных третьим лицам",`Мы не продаём и не передаём ваши персональные данные третьим лицам в коммерческих целях.

Данные могут быть переданы:
— Платёжным системам (СБП/банк-эквайер) — для проведения платежа;
— Органам государственной власти — по их законному требованию;
— Сервисам рассылки (только email, при наличии согласия на маркетинг).

Все третьи лица обязаны соблюдать конфиденциальность ваших данных.`],

          ["8. Ваши права",`В соответствии с ФЗ-152 «О персональных данных» вы имеете право:
— на доступ к вашим персональным данным;
— на исправление неточных данных;
— на удаление данных («право быть забытым»);
— на ограничение обработки;
— на отзыв согласия в любое время;
— на обжалование действий оператора в Роскомнадзоре.

Для реализации прав обратитесь: support@referat.io`],

          ["9. Безопасность данных",`Мы применяем технические и организационные меры для защиты ваших данных: шифрование передачи данных (HTTPS), ограничение доступа к базам данных, регулярный аудит безопасности.`],

          ["10. Изменения политики",`Мы вправе изменять настоящую Политику. При существенных изменениях пользователи будут уведомлены по email. Актуальная версия всегда доступна по адресу https://referat.io/privacy/

Редакция от 01.01.2026`],
        ].map(([title,text])=>(
          <div key={title} style={{marginBottom:28}}>
            <div className="LBL" style={{fontSize:10,color:C.black,marginBottom:10,borderBottom:`1px solid ${C.border}`,paddingBottom:8}}>{title}</div>
            <div style={{whiteSpace:"pre-wrap",color:C.gray}}>{text}</div>
          </div>
        ))}
      </div>
      <div style={{padding:"16px 28px",borderTop:`1px solid ${C.border}`,flexShrink:0}}>
        <button onClick={onClose}
          style={{width:"100%",padding:"12px",background:C.black,border:"none",color:"#fff",fontFamily:"'Barlow Condensed',sans-serif",fontWeight:700,fontSize:13,textTransform:"uppercase",letterSpacing:"0.12em",cursor:"pointer"}}>
          ЗАКРЫТЬ
        </button>
      </div>
    </ModalShell>
  );
}

// ─── APP ──────────────────────────────────────────────────────────────────────
function useScrolled(){
  const [s,set]=useState(false);
  useEffect(()=>{
    const fn=()=>set(window.scrollY>40);
    window.addEventListener("scroll",fn);
    return()=>window.removeEventListener("scroll",fn);
  },[]);
  return s;
}

export default function App(){
  const scrolled=useScrolled();
  const [menuOpen,setMenuOpen]=useState(false);
  const [count,setCount]=useState(270);
  const [showOrder,setShowOrder]=useState(false);
  const [orderPrefill,setOrderPrefill]=useState({});
  const [showOferta,setShowOferta]=useState(false);
  const [showPrivacy,setShowPrivacy]=useState(false);

  // Expose openers for use inside OrderModal agree checkboxes
  useEffect(()=>{
    window.__openOferta=()=>setShowOferta(true);
    window.__openPrivacy=()=>setShowPrivacy(true);
    return()=>{delete window.__openOferta;delete window.__openPrivacy;};
  },[]);

  useEffect(()=>{
    const iv=setInterval(()=>setCount(c=>c<340?c+1:c),3500);
    return()=>clearInterval(iv);
  },[]);

  const openOrder=(prefill={})=>{setOrderPrefill(prefill||{});setShowOrder(true);};

  return(
    <div style={{fontFamily:"'Barlow',sans-serif",background:"#fff"}}>
      <style>{GS}</style>
      <Header scrolled={scrolled} menuOpen={menuOpen} setMenuOpen={setMenuOpen} onOrder={openOrder}/>
      <main>
        <Hero count={count} onOrder={openOrder}/>
        <DemoGenerator onOrder={openOrder}/>
        <Reviews/>
        <HowItWorks onOrder={openOrder}/>
        <Universities/>
        <CompareTable onOrder={openOrder}/>
        <AgentsSection/>
        <Examples/>
        <Pricing onOrder={openOrder}/>
        <FAQSection/>
        <FinalCTA onOrder={openOrder}/>
      </main>
      <Footer onOferta={()=>setShowOferta(true)} onPrivacy={()=>setShowPrivacy(true)}/>

      {showOrder&&<OrderModal onClose={()=>setShowOrder(false)} prefill={orderPrefill}/>}
      {showOferta&&<OfertaModal onClose={()=>setShowOferta(false)}/>}
      {showPrivacy&&<PrivacyModal onClose={()=>setShowPrivacy(false)}/>}
    </div>
  );
}

