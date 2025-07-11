.. _admin_metadata_index:

Metadata
========

Onder het menu-item "Metadata" en op het dashboard onder het kopje "Metadata" wordt toegang geboden tot het beheer van:

* :ref:`admin_metadata_index_information_categories`
* :ref:`admin_metadata_index_organisations`
* :ref:`admin_metadata_index_themes`

Door hierop te klikken wordt het desbetreffende beheerscherm geopend.

.. _admin_metadata_index_information_categories:

Informatiecategorieën
---------------------

Toelichting
~~~~~~~~~~~

De `Wet open overheid`_ beschrijft 17 *informatiecategorieën*. Documenten die onder minstens één van deze categorieën vallen, moeten *actief* openbaar gemaakt worden. Dat wil zeggen dat een bestuursorgaan deze online moet publiceren, ook wanneer daar niet door een burger expliciet om gevraagd is in een *Woo-verzoek*.

Daarnaast vraagt de wet om ook documenten openbaar te maken die buiten deze *informatiecategorieën* vallen. Hiervoor geldt geen "harde" plicht, maar wel een *inspanningsverplichting*.

Overigens gelden op de plicht tot openbaarmaking ook een aantal uitzonderingen (hoofdstuk 5 van de wet). Raadpleeg voor meer informatie over de wet de jurist en/of informatiebeheerder van je eigen organisatie.

Voor de aansluiting op de landelijke `Woo-index`_ wordt ten zeerste geadviseerd om documenten te voorzien van metadata conform de `DiWoo`_-standaard. Deze standaard vereist onder meer dat in de metadata wordt vastgelegd op grond van welke *informatiecategorie(ën)* het document actief openbaar is gemaakt.

De 17 *informatiecategorieën* zijn opgenomen in de landelijke waardelijst `Woo informatiecategorieën`_. Deze lijst is al standaard opgenomen in het publicatiebank-component. Daarnaast bestaat de mogelijkheid, zoals we hieronder zullen beschrijven, om in het kader van de *inspanningsverplichting* hier voor de eigen organisatie *extra informatiecategorieën* aan toe te voegen.

In het publicatiebank-component leggen we de *informatiecategorieën* vast op de *publicatie* (in ontwikkeling). Dezelfde *informatiecategorieën* gelden voor de daaraan gekoppelde *documenten*.

.. warning:: Let op! Bij gebruik van het GPP-burgerportaal zullen zelf-toegevoegde informatiecategorieën op de landelijke `Woo-index`_ getoond worden als de informatiecategorie "inspanningsverplichting art 3.1 Woo". De landelijke Woo-index ondersteunt immers alleen de landelijke waardelijst.

Beheerscherm
~~~~~~~~~~~~

In het beheerscherm van de *informatiecategorieën* wordt een lijst getoond van alle *informatiecategorieën* die zijn opgeslagen in het publicatiebank-component.

Standaard staan de landelijke 17 verplichte *informatiecategorieën* hier al in. Zij zijn te herkennen aan de waarde "Waardelijst" in de kolom `Oorsprong` van de lijst.
Daarnaast bestaat er de mogelijkheid om voor de eigen organisatie *extra informatiecategorieën* toe te voegen. Deze zijn te herkennen aan de waarde "Zelf-toegevoegd item" in de kolom `Oorsprong` van de lijst.

Op het beheerscherm zijn de volgende acties mogelijk:

* Rechtboven zit een knop **informatiecategorie toevoegen** waarmee een *informatiecategorie* toegevoegd kan worden.
* Rechtboven zit een knop **toon API-resource-URLS** waarmee de lijst *informatiecategorieën* met resource-URI's wordt getoond. (technisch)
* Bovenaan zit een zoekveld met een knop **Zoeken** waarmee naar *informatiecategorieën* gezocht kan worden.
* Daaronder zit de mogelijkheid om **eenzelfde actie uit te voeren over meerdere informatiecategorieën**. Op dit moment wordt alleen de actie **Geselecteerde informatiecategorieën verwijderen** ondersteund. Merk op dat het mogelijk is om in de lijst één of meerdere *informatiecategorieën* aan te vinken.
* Onder de (bulk-)actie staat de lijst met *informatiecategorieën*. Door op de kolomtitels te klikken kan de lijst **alfabetisch geordend** worden.
* Rechts naast de lijst bestaat de mogelijkheid om deze te **filteren op oorsprong**.
* Bij een *informatiecategorie* kan op de `naam` geklikt worden om **de details in te zien** en deze eventueel **te wijzigen**.
* Bij een *informatiecategorie* kan op **Toon logs** (op één na rechter kolom) geklikt worden om direct de :ref:`audit trail<admin_logging_index>` in te zien.

Wanneer bij een *informatiecategorie* op  de `naam` wordt geklikt, wordt een scherm geopend met nadere details.
Hierop zien we:

* **Alle gegevens**. Deze lichten we hieronder toe.
* Rechtsboven een knop **Toon logs**. Deze toont de volledige :ref:`audit trail<admin_logging_index>` van de *informatiecategorie*.
* Rechtsboven een knop **Geschiedenis**. Deze toont de beheer-handelingen die vanuit de beheerinterface zijn uitgevoerd op de *informatiecategorie*.
* Linksonder de mogelijkheid om **wijzigingen op te slaan**. Er kan voor gekozen worden om na het opslaan direct een nieuwe *informatiecategorie* aan te maken of om direct de huidige *informatiecategorie* nogmaals te wijzigen.
* Rechtsonder de mogelijkheid om de *informatiecategorie* te **verwijderen**. Let op, dit wordt ten zeerste afgeraden voor informatiecategorieën uit de landelijke waardelijst!

Op een informatiecategorie zijn de volgende gegevens beschikbaar. Op het scherm worden verplichte velden **dikgedrukt** weergegeven.

**Algemene velden**

* ``Naam``. De naam van de *informatiecategorie*, bijvoorbeeld "convenant". Wanneer de informatiecategorie als ``oorsprong`` "Waadelijst heeft, dan is de waarde van dit veld niet te wijzigen.
* ``Naam meervoud``. De meervoudsvorm van de naam, bijvoorbeeld "convenanten". Wanneer de informatiecategorie als ``oorsprong`` "Waadelijst heeft, dan is de waarde van dit veld niet te wijzigen.
* ``Definitie``. De (mogelijk landelijke) definitie van de *informatiecategorie*. Wanneer de informatiecategorie als ``oorsprong`` "Waadelijst heeft, dan is de waarde van dit veld niet te wijzigen.
* ``Omschrijving``. De beknopte toelichting die aan medewerkers en burgers getoond wordt.
* ``Oorsprong``. Een niet-wijzigbaar, automatisch toegekende aanduiding van op welke wijze de *informatiecategorie* is toegevoegd; via de landelijke waardelijst of zelf toegevoegd.
* ``Identificatie``. De unieke IRI waarmee deze categorie gedefinieerd is in de landelijke waardelijst. Voor zelf-toegevoegde items wordt een identificatie gegenereerd.
* ``UUID``. Een niet-wijzigbaar, automatisch toegekend identificatiekenmerk.

**Archivering**

* ``Bron bewaartermijn``. De naam van de bron van de bewaartermijn. Doorgaans zal dit een selectielijst c.q. selectiebesluit zijn, welke conform de vigerende Archiefwet is vastgesteld.
* ``Selectiecategorie``. De specifieke categorie binnen de bron van de bewaartermijn.
* ``Archiefnominatie``. Een radioknop die aangeeft of de *publicaties* op termijn vernietigd of permanent bewaard moet worden. Permanent te bewaren *publicaties* moeten conform de vigerende Archiefwet op termijn overgebracht worden naar een archiefbewaarplaats c.q. plusdepot / e-depot.
* ``Bewaartermijn``. Het aantal jaar hoe lang de *publicaties* binnen de GPP-publicatiebank (of diens vervanger) bewaard moeten blijven tot actie (vernietiging dan wel overbrenging) genomen moet worden.
* ``Toelichting bewaartermijn``. Extra informatie die de (informatie-)beheerder kan aangeven.

.. Tip:: Wanneer de ``Archiefnominatie`` permanent te bewaren is, dan dient de ``Bewaartermijn`` 10 of 20 jaar te zijn, conform de **vigerende** Archiefwet.

.. _admin_metadata_index_organisations:

Organisaties
------------

Toelichting
~~~~~~~~~~~

De `Wet open overheid`_ kent voor alle Nederlandse bestuursorganen een verplichting om
documenten actief openbaar te maken. Mogelijk wordt vanuit één instantie/installatie
van het “Woo Publicaties”-component de openbaarmaking voor meerdere bestuursorganen
ondersteund. Denk daarbij bijvoorbeeld aan publicaties namens *de gemeente* en
publicaties namens *gemeenschappelijke regelingen* waaraan de gemeente deelneemt.
Of denk aan *shared service centres* die de ICT-diensten leveren voor meerdere gemeenten.

Het namens verschillende organisaties publiceren binnen één publicatieplatform wordt in
het “Woo Publicaties”-component ondersteund. In de admin-interface kan, zoals hieronder
wordt uitgelegd, een beheerder configureren namens welke organisaties gepubliceerd mag
worden. De organisatie wordt op iedere :ref:`publicatie <admin_publicaties_index>`
vastgelegd, zodat ook voor de burger inzichtelijk is van welke organisatie een
publicatie is. Ook zijn deze gegevens relevant om (op termijn) te toetsen in hoeverre
iedere organisatie voldoet aan de wettelijke openbaarmakingsplicht.

De landelijke `Woo-index`_ veronderstelt het gebruik van landelijke waardelijsten.
Deze worden bijgehouden door het `Register van Overheidsorganisaties (ROO) <https://organisaties.overheid.nl/>`_.
Standaard staan organisaties uit de volgende drie officiële waardelijsten al in het
“Woo Publicaties”-component ingelezen:

* `Gemeenten <https://standaarden.overheid.nl/tooi/waardelijsten/work?work_uri=https%3A%2F%2Fidentifier.overheid.nl%2Ftooi%2Fset%2Frwc_gemeenten_compleet>`_
* `Samenwerkingsorganisaties <https://standaarden.overheid.nl/tooi/waardelijsten/work?work_uri=https%3A%2F%2Fidentifier.overheid.nl%2Ftooi%2Fset%2Frwc_samenwerkingsorganisaties_compleet>`_
* `Overige overheidsorganisaties <https://standaarden.overheid.nl/tooi/waardelijsten/work?work_uri=https%3A%2F%2Fidentifier.overheid.nl%2Ftooi%2Fset%2Frwc_overige_overheidsorganisaties_compleet>`_

.. warning:: Let op! In de admin-interface bestaat de mogelijkheid om *extra organisaties*
   toe te voegen. Hieraan gekoppelde publicaties zullen niet gevonden worden
   via de landelijke `Woo-index`_! Zij kunnen wel gevonden worden via het burgerportaal
   van het GPP-Woo.

Beheerscherm
~~~~~~~~~~~~

In het beheerscherm van de *organisaties* wordt een lijst getoond van alle
*organisaties* die zijn opgeslagen in het publicatiebank-component.

Standaard staan organisaties uit drie officiële waardelijsten hier al in (zie toelichting
hierboven).

Deze zijn te herkennen via de *Oorsprong* kolom. Organisaties uit de waardelijsten kunnen
niet gewijzigd worden - ze kunnen enkel
:ref:`geactiveerd of gedeactiveerd worden <admin_metadata_index_organisation_active>`.
Daarnaast bestaat de mogelijkheid om voor de eigen organisatie *extra organisaties*
toe te voegen. Deze zijn de herkennen aan de waarde "Zelf-toegevoegd item" in de kolom
*Oorsprong* van de lijst. Deze kunnen indien nodig gewijzigd worden.

Op het beheerscherm zijn de volgende acties mogelijk:

* Rechtsboven zit een knop **organisatie toevoegen** waarmee een *organisatie* toegevoegd kan worden.
* Bovenaan zit een zoekveld met een knop **Zoeken** waarmee naar *organisaties* gezocht kan worden.
* Daaronder zit de mogelijkheid om **eenzelfde actie uit te voeren over meerdere organisaties**.
  Op dit moment wordt alleen de actie **Geselecteerde organisaties verwijderen** ondersteund.
  Merk op dat het mogelijk is om in de lijst één of meerdere *organisaties* aan te vinken.
* Onder de (bulk-)actie staat de lijst met *organisaties*. Door op de kolomtitels te klikken kan de lijst **alfabetisch geordend** worden.
* Rechts naast de lijst bestaat de mogelijkheid om deze te **filteren op oorsprong en/of status**.
* Bij een *organisatie* kan op de *naam* geklikt worden om **de details in te zien** en deze eventueel **te wijzigen** en/of (de)activeren.
* Bij een *organisatie* kan op **Toon logs** (op één na rechter kolom) geklikt worden om direct de :ref:`audit trail<admin_logging_index>` in te zien.

Wanneer bij een *organisatie* op de *naam* wordt geklikt, dan opent een scherm met nadere details. Hierop zien we:

* **Alle gegevens**. Deze lichten we hieronder toe.
* Rechtsboven een knop **Toon logs**. Deze toont de volledige :ref:`audit trail<admin_logging_index>` van de *organisatie*.
* Rechtsboven een knop **Geschiedenis**. Deze toont de beheer-handelingen die vanuit de beheerinterface zijn uitgevoerd op de *organisatie*.
* Linksonder de mogelijkheid om **wijzigingen op te slaan**. Er kan voor gekozen worden om na het opslaan direct een nieuwe *organisatie* aan te maken of om direct de huidige *organisatie* nogmaals te wijzigen.
* Rechtsonder de mogelijkheid om de *organisatie* te **verwijderen**.

Op een organisatie zijn de volgende gegevens beschikbaar. Op het scherm worden verplichte velden **dikgedrukt** weergegeven.

* ``Is actief``. Een selectievakje die aangeeft of de organisatie geactiveerd is of niet.
  Om een organisatie te activeren klik je het vinkje aan, om een organisatie te deactiveren schakel je het vinkje uit, en sla de wijzigingen op.
* ``RSIN``. Het `RSIN <https://www.kvk.nl/over-het-handelsregister/rsin-nummer/>`_ van de organisatie.
* ``UUID``. Een niet-wijzigbaar, automatisch toegekend identificatiekenmerk.
* ``Oorsprong``. Een niet-wijzigbaar, automatisch toegekende aanduiding die aangeeft uit welke landelijke waardelijst de organisatie komt, of dat deze zelf toegevoegd is door een beheerder.
* ``Naam``. De naam van de *organistaie*, bijvoorbeeld "Politie".

.. _admin_metadata_index_organisation_active:

Activeren/deactiveren van organisaties
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Bij een nieuwe installatie zijn standaard alle organisaties gedeactiveerd. Een beheerder
dient de gewenste organisaties te activeren om ze in gebruik te nemen.

Als een organisatie gedeactiveerd is, dan kunnen er geen nieuwe publicaties aan gekoppeld
worden. Als je een organisatie deactiveert waaraan al bestaande publicaties hangen, dan
heeft dit geen invloed op de bestaande publicaties.

.. _admin_metadata_index_themes:

Thema's
-------

.. warning:: Thema's kunnen nog niet gelinkt worden aan publicaties. Deze wens staat nog op de backlog / roadmap.

Toelichting
~~~~~~~~~~~

Om de vindbaarheid van openbare documenten te bevorderen ondersteunt de `DiWoo`_-standaard het toekennen van een of meerdere *thema's* aan openbare documenten. Hiervoor is een landelijke waardelijst gedefinieerd: `Thema-indeling voor Officiële Publicaties (TOP-lijst)`_. Op de `Woo-index`_ kan een burger zoeken naar openbare documenten, die aan een bepaald thema gekoppeld zijn.

De landelijke thema-lijst is ook standaard ingelezen in en wordt ontsloten met het "Woo-publicaties"-component, zodat deze gebruikt kan worden bij het registreren en vindbaar maken van openbare documenten.

In het publicatiebank-component leggen we de *thema's* vast op de *publicatie* (in ontwikkeling). Dezelfde *thema's* gelden voor de daaraan gekoppelde *documenten*.

De `DiWoo`_-standaard ondersteunt alleen het gebruik van de landelijke waardelijst `Thema-indeling voor Officiële Publicaties (TOP-lijst)`_. Ook op de `Woo-index`_ kan alleen op deze *thema's*  gezocht worden naar openbare documenten.

Beheerscherm
~~~~~~~~~~~~

In het beheerscherm van de *thema's* wordt een lijst getoond van alle thema's die zijn opgeslagen in het "WOO Publications"-component. Standaard staan de landelijke thema's hier al in.

Op het beheerscherm zijn de volgende acties mogelijk:

* Bovenaan zit een zoekveld met een knop **Zoeken** waarmee naar *thema's* gezocht kan worden.
* Daaronder zit de mogelijkheid om **eenzelfde actie uit te voeren over meerdere informatiecategorieën**. Op dit moment wordt alleen de actie **Geselecteerde thema's verwijderen** ondersteund. Merk op dat het mogelijk is om in de lijst één of meerdere *thema's* aan te vinken.
* Onder de (bulk-)actie staat de lijst met *thema's*.
* Bij een *thema* kan op de `naam` geklikt worden om **de details in te zien**.
* Bij een *thema* kan op **Toon logs** (rechter kolom) geklikt worden om direct de :ref:`audit trail<admin_logging_index>` in te zien.

Wanneer bij een *thema* op  de `naam` wordt geklikt, wordt een scherm geopend met nadere details.
Hierop zien we:

* **Alle gegevens**. Deze lichten we hieronder toe.
* Rechtsboven een knop **Toon logs**. Deze toont de volledige :ref:`audit trail<admin_logging_index>` van het *thema*.
* Rechtsboven een knop **Geschiedenis**. Deze toont de beheer-handelingen die vanuit de Admin-interface zijn uitgevoerd op het *thema*.
* Linksonder een knop om het scherm te **sluiten** en teurg te keren naar de lijst.
* Rechtsonder de mogelijkheid om het *thema* te **verwijderen**.

Op een *thema* zijn de volgende gegevens beschikbaar.

* ``UUID``. Een niet-wijzigbaar, automatisch toegekend identificatie kenmerk.
* ``Naam``. De naam van het *thema*, bijvoorbeeld "cultuur en recreatie".
* ``position``. *systeemveld*
* ``ref node id``. *systeemveld*


.. _Wet open overheid: https://wetten.overheid.nl/BWBR0045754/
.. _Woo-index: https://open.overheid.nl/
.. _DiWoo: https://standaarden.overheid.nl/diwoo/metadata
.. _Woo informatiecategorieën: https://standaarden.overheid.nl/tooi/waardelijsten/work?work_uri=https%3A%2F%2Fidentifier.overheid.nl%2Ftooi%2Fset%2Fscw_woo_informatiecategorieen
.. _Thema-indeling voor Officiële Publicaties (TOP-lijst): https://standaarden.overheid.nl/tooi/waardelijsten/work?work_uri=https%3A%2F%2Fidentifier.overheid.nl%2Ftooi%2Fset%2Fscw_toplijst
