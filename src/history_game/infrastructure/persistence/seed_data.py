"""Curated 24-event World History seed dataset and idempotent catalog seeder."""

from __future__ import annotations

from typing import Final

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from history_game.domain.entities import HistoricalEvent
from history_game.domain.value_objects import HistoricalEra, HistoricalYear
from history_game.infrastructure.persistence.models import HistoricalEventModel

SEED_HISTORICAL_EVENTS: Final[tuple[HistoricalEvent, ...]] = (
    # Ancient World (3500 BCE – 500 BCE)
    HistoricalEvent(
        id="evt-cuneiform-writing",
        title="Development of Sumerian Cuneiform Writing",
        year=HistoricalYear(-3200),
        era=HistoricalEra.ANCIENT,
        region="Mesopotamia",
        summary=(
            "Sumerian scribes in Uruk press wedge-shaped reed styluses into wet clay "
            "tablets to record grain harvests, temple tribute, and commercial contracts."
        ),
        significance=(
            "Inaugurated recorded human history by enabling durable legal, economic, "
            "and literary archives across the Fertile Crescent."
        ),
    ),
    HistoricalEvent(
        id="evt-great-pyramid-giza",
        title="Completion of the Great Pyramid of Giza",
        year=HistoricalYear(-2560),
        era=HistoricalEra.ANCIENT,
        region="Egypt",
        summary=(
            "Egyptian royal architects and tens of thousands of skilled quarry workers "
            "complete a monumental limestone tomb on the Giza Plateau for Pharaoh Khufu."
        ),
        significance=(
            "Stood as the tallest human-made structure for millennia and exemplified "
            "Old Kingdom state organization and geometric engineering."
        ),
    ),
    HistoricalEvent(
        id="evt-code-of-hammurabi",
        title="Promulgation of the Code of Hammurabi",
        year=HistoricalYear(-1750),
        era=HistoricalEra.ANCIENT,
        region="Babylon",
        summary=(
            "A Babylonian monarch carved nearly three hundred civil, property, and "
            "criminal laws in Akkadian cuneiform onto towering black basalt steles."
        ),
        significance=(
            "Established one of the earliest comprehensive written legal codes with "
            "standardized judicial procedures and public accountability."
        ),
    ),
    HistoricalEvent(
        id="evt-cyrus-cylinder",
        title="Cyrus the Great Captures Babylon and Issues the Cyrus Cylinder",
        year=HistoricalYear(-539),
        era=HistoricalEra.ANCIENT,
        region="Persia / Mesopotamia",
        summary=(
            "The founder of the Achaemenid Empire enters Babylon peacefully and "
            "inscribes a clay cylinder restoring displaced peoples and local sanctuaries."
        ),
        significance=(
            "Created an enduring model of multi-ethnic imperial governance, religious "
            "toleration, and regional administrative autonomy."
        ),
    ),
    # Classical Era (500 BCE – 500 CE)
    HistoricalEvent(
        id="evt-ashoka-edicts",
        title="Emperor Ashoka Inscribes the Major Rock and Pillar Edicts",
        year=HistoricalYear(-250),
        era=HistoricalEra.CLASSICAL,
        region="South Asia",
        summary=(
            "Following the devastating Kalinga campaign, the Mauryan ruler carves "
            "proclamations of non-violence, civic welfare, and moral duty across India."
        ),
        significance=(
            "Catalyzed the trans-Asian spread of Buddhism and articulated an ethical "
            "vision of statecraft grounded in compassion and religious pluralism."
        ),
    ),
    HistoricalEvent(
        id="evt-qin-unification",
        title="Unification of China Under Qin Shi Huang",
        year=HistoricalYear(-221),
        era=HistoricalEra.CLASSICAL,
        region="East Asia",
        summary=(
            "The ruler of the western state of Qin conquers the last rival Warring "
            "States kingdom and standardizes scripts, coinage, axle widths, and weights."
        ),
        significance=(
            "Forged the institutional framework of imperial China that endured across "
            "subsequent dynasties for more than two millennia."
        ),
    ),
    HistoricalEvent(
        id="evt-rosetta-stone",
        title="Inscribing of the Rosetta Stone Decree at Memphis",
        year=HistoricalYear(-196),
        era=HistoricalEra.CLASSICAL,
        region="Egypt",
        summary=(
            "Ptolemaic priests issue a royal decree honoring King Ptolemy V carved "
            "into black granodiorite in hieroglyphic, Demotic, and Ancient Greek scripts."
        ),
        significance=(
            "Provided the linguistic key that centuries later enabled scholars to "
            "decipher ancient Egyptian hieroglyphs."
        ),
    ),
    HistoricalEvent(
        id="evt-cai-lun-paper",
        title="Cai Lun Refines the Imperial Papermaking Process",
        year=HistoricalYear(105),
        era=HistoricalEra.CLASSICAL,
        region="East Asia",
        summary=(
            "A Han court official presents the emperor with lightweight writing sheets "
            "manufactured from mulberry bark, hemp fibers, rags, and fishing nets."
        ),
        significance=(
            "Replaced costly silk and heavy bamboo slips, revolutionizing literacy, "
            "bureaucratic record-keeping, and book production worldwide."
        ),
    ),
    # Medieval Era (500 CE – 1450 CE)
    HistoricalEvent(
        id="evt-house-of-wisdom",
        title="Expansion of the House of Wisdom in Baghdad",
        year=HistoricalYear(830),
        era=HistoricalEra.MEDIEVAL,
        region="Middle East",
        summary=(
            "Abbasid Caliph al-Ma'mun patronizes an international academy where scholars "
            "translate Greek, Persian, and Sanskrit treatises and pioneer algebra."
        ),
        significance=(
            "Preserved classical antiquity and advanced mathematics, optics, astronomy, "
            "and medicine during the Islamic Golden Age."
        ),
    ),
    HistoricalEvent(
        id="evt-bi-sheng-movable-type",
        title="Bi Sheng Invents Ceramic Movable-Type Printing",
        year=HistoricalYear(1040),
        era=HistoricalEra.MEDIEVAL,
        region="East Asia",
        summary=(
            "A Song Dynasty artisan carves individual Chinese characters into clay "
            "cubes, bakes them in a kiln, and arranges them on iron frames coated in resin."
        ),
        significance=(
            "Pioneered modular movable-type printing centuries before European presses, "
            "expanding scholarly publishing across East Asia."
        ),
    ),
    HistoricalEvent(
        id="evt-magna-carta",
        title="Sealing of Magna Carta at Runnymede",
        year=HistoricalYear(1215),
        era=HistoricalEra.MEDIEVAL,
        region="Europe",
        summary=(
            "English barons compel King John to affix the royal seal to a charter "
            "limiting arbitrary taxation and guaranteeing lawful judgment by peers."
        ),
        significance=(
            "Established the foundational constitutional principle that the sovereign "
            "is subject to the rule of law."
        ),
    ),
    HistoricalEvent(
        id="evt-mansa-musa-pilgrimage",
        title="Mansa Musa's Trans-Saharan Pilgrimage from the Mali Empire",
        year=HistoricalYear(1324),
        era=HistoricalEra.MEDIEVAL,
        region="West Africa / Middle East",
        summary=(
            "The ruler of the Mali Empire leads a vast caravan across the Sahara to "
            "Cairo and Mecca, distributing West African gold and endowing libraries in Timbuktu."
        ),
        significance=(
            "Placed the Mali Empire on Mediterranean world maps and transformed "
            "Timbuktu into a premier center of Islamic scholarship and trade."
        ),
    ),
    # Early Modern Era (1450 CE – 1750 CE)
    HistoricalEvent(
        id="evt-gutenberg-press",
        title="Gutenberg Introduces the Mechanical Movable-Type Printing Press",
        year=HistoricalYear(1450),
        era=HistoricalEra.EARLY_MODERN,
        region="Europe",
        summary=(
            "A goldsmith in Mainz combines a precision hand-cast metal type alloy, "
            "oil-based printing ink, and a wooden screw press to mass-produce books."
        ),
        significance=(
            "Sparked the European information revolution, accelerating Renaissance "
            "humanism, the Reformation, and scientific exchange."
        ),
    ),
    HistoricalEvent(
        id="evt-copernicus-heliocentrism",
        title="Publication of Copernicus's Heliocentric Treatise",
        year=HistoricalYear(1543),
        era=HistoricalEra.EARLY_MODERN,
        region="Europe",
        summary=(
            "A Polish astronomer publishes De revolutionibus orbium coelestium, "
            "demonstrating mathematically that Earth and the planets orbit the Sun."
        ),
        significance=(
            "Launched the Scientific Revolution by challenging geocentric cosmology "
            "and inspiring Galileo and Kepler."
        ),
    ),
    HistoricalEvent(
        id="evt-peace-of-westphalia",
        title="Signing of the Peace of Westphalia",
        year=HistoricalYear(1648),
        era=HistoricalEra.EARLY_MODERN,
        region="Europe",
        summary=(
            "Diplomatic congresses in Munster and Osnabruck conclude the Thirty Years' "
            "War through multilateral treaties recognizing territorial state sovereignty."
        ),
        significance=(
            "Laid the legal foundation for the modern international system of sovereign "
            "nation-states and diplomatic congresses."
        ),
    ),
    HistoricalEvent(
        id="evt-newton-principia",
        title="Isaac Newton Publishes the Principia Mathematica",
        year=HistoricalYear(1687),
        era=HistoricalEra.EARLY_MODERN,
        region="Europe",
        summary=(
            "An English physicist formulates the three laws of motion and the law of "
            "universal gravitation, unifying terrestrial and celestial mechanics."
        ),
        significance=(
            "Provided the mathematical bedrock of classical physics and Enlightenment "
            "scientific inquiry for more than two centuries."
        ),
    ),
    # Industrial Age (1750 CE – 1914 CE)
    HistoricalEvent(
        id="evt-watt-steam-engine",
        title="James Watt Patents the Separate-Condenser Steam Engine",
        year=HistoricalYear(1769),
        era=HistoricalEra.INDUSTRIAL,
        region="Europe",
        summary=(
            "A Scottish instrument maker adds a separate condensing chamber to the "
            "atmospheric steam engine, drastically reducing fuel consumption in mines and mills."
        ),
        significance=(
            "Powered the Industrial Revolution by untethering manufacturing and transport "
            "from seasonal waterwheels and wind."
        ),
    ),
    HistoricalEvent(
        id="evt-haitian-independence",
        title="Proclamation of Haitian Independence",
        year=HistoricalYear(1804),
        era=HistoricalEra.INDUSTRIAL,
        region="Caribbean / Americas",
        summary=(
            "Formerly enslaved revolutionaries defeat European expeditionary forces in "
            "Saint-Domingue and establish the sovereign republic of Haiti."
        ),
        significance=(
            "Created the first independent nation in Latin America and the first "
            "republic founded through a successful slave uprising."
        ),
    ),
    HistoricalEvent(
        id="evt-meiji-restoration",
        title="Proclamation of the Meiji Restoration in Japan",
        year=HistoricalYear(1868),
        era=HistoricalEra.INDUSTRIAL,
        region="East Asia",
        summary=(
            "Reformist leaders abolish the Tokugawa shogunate, restore imperial rule in "
            "Tokyo, and launch rapid industrialization and constitutional modernization."
        ),
        significance=(
            "Transformed Japan from an isolated feudal society into a major industrial "
            "and technological power within a single generation."
        ),
    ),
    HistoricalEvent(
        id="evt-wright-brothers-flight",
        title="First Controlled Powered Airplane Flight at Kitty Hawk",
        year=HistoricalYear(1903),
        era=HistoricalEra.INDUSTRIAL,
        region="North America",
        summary=(
            "Two bicycle engineers from Ohio achieve sustained, controlled, heavier-than-air "
            "powered flight across the sand dunes of North Carolina."
        ),
        significance=(
            "Inaugurated the aviation age, shrinking global travel times and reshaping "
            "international commerce and transportation."
        ),
    ),
    # Modern Era (1914 CE – Present)
    HistoricalEvent(
        id="evt-fleming-penicillin",
        title="Alexander Fleming Discovers Penicillin",
        year=HistoricalYear(1928),
        era=HistoricalEra.MODERN,
        region="Europe",
        summary=(
            "A Scottish bacteriologist observes that a Penicillium mold colony on a "
            "laboratory petri dish dissolves surrounding Staphylococcus bacteria."
        ),
        significance=(
            "Ushered in the era of modern antibiotics, saving hundreds of millions of "
            "lives from previously fatal bacterial infections."
        ),
    ),
    HistoricalEvent(
        id="evt-universal-declaration-human-rights",
        title="Adoption of the Universal Declaration of Human Rights",
        year=HistoricalYear(1948),
        era=HistoricalEra.MODERN,
        region="Global",
        summary=(
            "Meeting at the Palais de Chaillot in Paris, the United Nations General "
            "Assembly adopts thirty articles affirming fundamental rights for all people."
        ),
        significance=(
            "Established the global legal and moral standard for international human "
            "rights treaties and post-war constitutional protections."
        ),
    ),
    HistoricalEvent(
        id="evt-apollo-11-moon-landing",
        title="Apollo 11 First Crewed Lunar Landing",
        year=HistoricalYear(1969),
        era=HistoricalEra.MODERN,
        region="Space / Global",
        summary=(
            "Astronauts aboard the lunar module Eagle touch down on the Sea of "
            "Tranquility and broadcast humanity's first footsteps on another world."
        ),
        significance=(
            "Demonstrated the pinnacle of spacefaring engineering, satellite telemetry, "
            "and integrated circuit computing."
        ),
    ),
    HistoricalEvent(
        id="evt-world-wide-web-public",
        title="CERN Releases the World Wide Web into the Public Domain",
        year=HistoricalYear(1993),
        era=HistoricalEra.MODERN,
        region="Europe / Global",
        summary=(
            "Tim Berners-Lee and CERN place the hypertext transfer protocol, HTML, "
            "and browser software into the public domain royalty-free for all users."
        ),
        significance=(
            "Ignited the global Internet era, transforming human communication, "
            "education, commerce, and knowledge sharing."
        ),
    ),
)


async def seed_catalog_if_empty(
    session_factory: async_sessionmaker[AsyncSession],
) -> int:
    """Insert the 24 curated historical events if the historical_events table is empty."""
    async with session_factory() as session:
        count_stmt = select(func.count()).select_from(HistoricalEventModel)
        existing_count = (await session.execute(count_stmt)).scalar_one()
        if existing_count > 0:
            return 0

        rows = [
            HistoricalEventModel(
                id=event.id,
                title=event.title,
                year=event.year.value,
                era=event.era.value,
                region=event.region,
                summary=event.summary,
                significance=event.significance,
            )
            for event in SEED_HISTORICAL_EVENTS
        ]
        session.add_all(rows)
        await session.commit()
        return len(rows)
