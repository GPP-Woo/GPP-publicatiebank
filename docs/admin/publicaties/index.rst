.. _admin_publicaties_index:

Publicaties
============

Onder het menu-item "Publicaties" en op het dashboard onder het kopje "Publicaties" wordt toegang geboden tot het beheer van:

* :ref:`admin_publicaties_index_documenten`
* :ref:`admin_publicaties_index_publicaties`
* :ref:`admin_publicaties_index_onderwerpen`

Door hierop te klikken wordt het desbetreffende beheerscherm geopend.

.. _admin_publicaties_index_documenten:

Documenten
-----------

Een *document* bestaat uit een bestand (bijvoorbeeld een PDF) en metadata. Een *document* hoort altijd bij een :ref:`publicatie <admin_publicaties_index_publicaties>`.

In het beheerscherm van de *documenten* wordt een lijst getoond van alle *document*-registraties, die zijn opgeslagen in de GPP-publicatiebank.
Op dit scherm zijn de volgende acties mogelijk:

* Rechtboven zit een knop **document toevoegen** waarmee een registratie toegevoegd kan worden.
* Bovenaan zit een zoekveld met een knop **Zoeken** waarmee in de registraties gezocht kan worden.
* Direct onder de zoekbalk zit de mogelijkheid om de lijst te **filteren op een specifieke registratiejaar**.
* Daaronder zit de mogelijkheid om **eenzelfde actie uit te voeren over meerdere documentregistraties**. Op dit moment worden de acties **Geselecteerde documenten verwijderen**, **Verstuur de geselecteerde documenten naar de zoekindex**, **Verwijder de geselecteerde documenten uit de zoekindex**, **Trek gepubliceerde documenten in** en **Wijzig de eigenaren van het document** ondersteund. Merk op dat het mogelijk is om in de lijst één of meerdere *document*-registraties aan te vinken.
* Onder de (bulk-)actie staat de lijst met *document*-registraties. Door op de kolomtitels te klikken kan de lijst **alfabetisch of chronologisch geordend** worden.
* Rechts naast de lijst bestaat de mogelijkheid om deze te **filteren op registratiedatum, creatiedatum en/of publicatiestatus**.
* Bij een *document*-registratie kan op de `officiële titel` geklikt worden om **de details in te zien** en deze eventueel **te wijzigen**.
* Bij een *document*-registratie kan op **Toon logs** (rechter kolom) geklikt worden om direct de :ref:`audit trail<admin_logging_index>` in te zien.

Wanneer bij een *document*-registratie op  de `officiële titel` wordt geklikt, wordt een scherm geopend met de *document*-details.
Hierop zien we:

* **Alle metadatavelden**. Deze lichten we hieronder toe.
* Rechtsboven een knop **Toon logs**. Deze toont de volledige :ref:`audit trail<admin_logging_index>` van de *document*-registratie.
* Rechtsboven een knop **Geschiedenis**. Deze toont de beheer-handelingen die vanuit de Admin-interface zijn uitgevoerd op de registratie.
* Linksonder de mogelijkheid om **wijzigingen op te slaan**. Er kan voor gekozen worden om na het opslaan direct een nieuwe registratie aan te maken of om direct de huidige registratie nogmaals te wijzigen.
* Rechtsonder de mogelijkheid om de registratie te **verwijderen**.

Op een *document*-registratie zijn de volgende metadata beschikbaar. Op het scherm worden verplichte velden **dikgedrukt** weergegeven.

**Algemene velden**

* ``Publicatie``. Het *document* moet hier gekoppeld worden aan een bestaande of nieuwe *publicatie*
* ``Identificatie``. Het unieke kenmerk dat intern aan het *document* is toegekend, bijvoorbeeld door het zaaksysteem of het DMS. (DiWoo: ``identifier``)
* ``Officiële titel``. De (mogelijk uitgebreide) officiële titel van het document. (DiWoo: ``officieleTitel``)
* ``Verkorte titel``. De verkorte titel / citeertitel van het document. (DiWoo: ``verkorteTitel``)
* ``Omschrijving``. Een beknopte omschrijving / samenvatting van de inhoud van het document. (DiWoo: ``omschrijving``)
* ``Creatiedatum``. De datum waarop het document gecreëerd is. Deze ligt doorgaans voor of op de registratiedatum.  (DiWoo: ``creatiedatum``)
* ``Bestandsformaat``. *In ontwikkeling* (DiWoo: ``format``)
* ``Bestandsnaam``. Naam van het bestand zoals deze op de harde schijf opgeslagen wordt.
* ``Bestandsomvang`` Bestandsgrootte, in aantal bytes.
* ``Status``. De publicatiestatus van het document. "Gepubliceerd" betekent dat het document online vindbaar en raadpleegbaar is. "Concept" en "Ingetrokken" zijn offline voor de buitenwereld.
* ``Gepubliceerd Op``. De niet-wijzigbare datum en tijd waarop het document is gepubliceerd.
* ``Ingetrokken Op``. De niet-wijzigbare datum en tijd waarop het document is ingetrokken.
* ``Geregistreerd op``. De niet-wijzigbare datum en tijd waarop het document nieuw is toegevoegd.
* ``Laatst gewijzigd op``. De niet-wijzigbare datum en tijd waarop het document voor het laatst gewijzigd is.
* ``Ontvangen op``. De datum waarop het document in ontvangst is genomen.
* ``Ondertekend op``. De datum waarop het document intern is ondertekend.
* ``Eigenaar``. Deze wordt doorgaans afegeleid van de gekoppelde *publicatie*. In de GPP-app kan alleen de "eigenaar" de publicatie wijzigen. De "eigenaar" is altijd een medewerker.
* ``UUID``. Een niet-wijzigbaar, automatisch toegekend identificatiekenmerk. (DiWoo: ``identifier``)

**Documenten-API-koppeling**

* ``Documents API Service``. Systeemveld, bevat de verwijzing naar het bestand in de Documenten API.
* ``Document UUID``. Systeemveld, bevat de verwijzing naar het bestand in de Documenten API.
* ``Documentvergrendelingscode``. Systeemveld, bevat de vergrendelingscode van een bestand in de Documenten API.
* ``Upload voltooid``. Systeemveld, houdt bij of het bestand volledig naar de Documenten API doorgezet is.

**Kenmerken**

* Aan ieder document kan geen, een of meerdere combinaties van een ``identificatie`` en een ``bron`` gegeven worden. Dit kan bijvoorbeeld een documentnummer (identificatie) uit een aanleverend zaaksysteem of DMS (bron) zijn.

.. _admin_publicaties_index_publicaties:

Publicaties
------------

Een *publicatie* bestaat uit een aantal gegevens met doorgaans een of meerdere :ref:`documenten <admin_publicaties_index_documenten>` (zie hierboven).

.. tip::

    Het toevoegen van een document aan een *publicatie* is niet verplicht. Daarmee kan
    voldaan worden aan:

        (...) Van een gehele niet-openbaarmaking doet het bestuursorgaan mededeling op
        de wijze en het tijdstip waarop het niet-openbaar gemaakte stuk openbaar zou
        zijn gemaakt.

        -- `Wet open overheid, art. 3.3, lid 8`_

    In het veld ``Omschrijving`` kan de mededeling opgenomen worden.

.. tip::

    Bij het aanmaken of bewerken van een *publicatie* met de `publicatiestatus` **Concept** zijn
    de velden behalve de `officiële titel` niet verplicht.

In het beheerscherm van de *publicaties* wordt een lijst getoond van alle *publicatie*-registraties, die zijn opgeslagen in het publicatiebank-component.
Op dit scherm zijn de volgende acties mogelijk:

* Rechtboven zit een knop **publicatie toevoegen** waarmee een registratie toegevoegd kan worden.
* Bovenaan zit een zoekveld met een knop **Zoeken** waarmee in de registraties gezocht kan worden.
* Direct onder de zoekbalk zit de mogelijkheid om de lijst te **filteren op een specifieke registratiejaar**.
* Daaronder zit de mogelijkheid om **eenzelfde actie uit te voeren over meerdere publicaties**. Op dit moment worden de acties **Geselecteerde publicaties verwijderen**, **Verstuur de geselecteerde publicaties naar de zoekindex**, **Verwijder de geselecteerde publicaties uit de zoekindex**, **Trek gepubliceerde publicaties in**, **Geselecteerde publicaties herwaarderen** en **Wijzig de eigenaren van de publicaties** ondersteund. Merk op dat het mogelijk is om in de lijst één of meerdere *publicatie*-registraties aan te vinken.
* Onder de (bulk-)actie staat de lijst met *publicatie*-registraties. Door op de kolomtitels te klikken kan de lijst **alfabetisch of chronologisch geordend** worden.
* Rechts naast de lijst bestaat de mogelijkheid om deze te **filteren op registratiedatum, publicatiestatus, archiefnominatie en/of archiefactiedatum**.
* Bij een *publicatie*-registratie kan op de `officiële titel` geklikt worden om **de details in te zien** en deze eventueel **te wijzigen**.
* Bij een *publicatie*-registratie kan op **Toon documenten** (rechter kolom) geklikt worden om direct de gekoppelde *documenten* in te zien.
* Bij een *publicatie*-registratie kan op **Toon logs** (rechter kolom) geklikt worden om direct de :ref:`audit trail<admin_logging_index>` in te zien.
* Bij een *publicatie*-registratie kan op **Open in app** (rechter kolom) geklikt worden om de URL te openen zoals bij de :ref:`admin_configuratie_index_alg_inst` geconfigureerd is. Let op, alle de `eigenaar` van een publicatie kan deze in de (GPP-)app openen!
* Bij een *publicatie*-registratie kan op **Open in burgerportaal** (rechter kolom) geklikt worden om de URL te openen zoals bij de :ref:`admin_configuratie_index_alg_inst` geconfigureerd is.

Wanneer bij een *publicatie*-registratie op  de `officiële titel` wordt geklikt, wordt een scherm geopend met de *publicatie*-details.
Hierop zien we:

* **Alle metadatavelden**. Deze lichten we hieronder toe.
* Rechtsboven een knop **Toon logs**. Deze toont de volledige :ref:`audit trail<admin_logging_index>` van de *publicatie*-registratie.
* Rechtsboven een knop **Geschiedenis**. Deze toont de beheer-handelingen die vanuit de Admin-interface zijn uitgevoerd op de registratie.
* Onder de metadatavelden de gekoppelde *documenten*. De metadata die getoond en gewijzigd kan worden komt overeen met zoals hierboven beschreven. Een *document* kan ook verwijderd worden door dit aan de rechterzijde aan te vinken. Let op, dit betreft niet alleen het ontkoppelen van een *document*, maar de volledige verwijdering!
* Onder de *documenten* de mogelijkheid om **een nieuw document** toe te voegen aan de *publicatie*.
* Linksonder de mogelijkheid om **wijzigingen op te slaan**. Er kan voor gekozen worden om na het opslaan direct een nieuwe registratie aan te maken of om direct de huidige registratie nogmaals te wijzigen.
* Rechtsonder de mogelijkheid om de registratie te **verwijderen**.

Op een *publicatie*-registratie zijn de volgende metadata beschikbaar. Op het scherm worden verplichte velden **dikgedrukt** weergegeven.

**Algemene velden**

* ``Informatiecategorieën`` De informatiecategorieën die het soort informatie verduidelijken binnen de publicatie (DiWoo: ``informatieCategorieen``)
* ``Onderwerpen`` Onderwerpen omvatten maatschappelijk relevante kwesties waar meerdere publicaties aan gekoppeld zijn. Onderwerpen kunnen tientallen jaren relevant blijven.
* ``Publisher`` De organisatie die de publicatie heeft gepubliceerd. (DiWoo: ``publisher``)
* ``Verantwoordelijke`` De organisatie die de verantwoordelijk is voor de publicatie. (DiWoo: ``verantwoordelijke``)
* ``Opsteller`` De organisatie die de publicatie opgesteld heeft. (DiWoo: ``opsteller``)
* ``Officiële titel``. De (mogelijk uitgebreide) officiële titel van de publicatie. (DiWoo: ``officieleTitel``)
* ``Verkorte titel``. De verkorte titel / citeertitel van de publicatie. (DiWoo: ``verkorteTitel``)
* ``Omschrijving``. Een beknopte omschrijving / samenvatting van de publicatie. (DiWoo: ``omschrijving``)
* ``Status``. De status van de publicatie. "Gepubliceerd" betekent dat de publicatie online vindbaar en raadpleegbaar is. "Concept" en "Ingetrokken" zijn offline voor de buitenwereld.
  Let op, als je een publicatie intrekt, dan worden de documenten met de huidige status "Gepubliceerd" automatisch ook ingetrokken!
* ``Gepubliceerd Op``. De niet-wijzigbare datum en tijd waarop de publicatie is gepubliceerd.
* ``Ingetrokken Op``. De niet-wijzigbare datum en tijd waarop de publicatie is ingetrokken.
* ``Geregistreerd op``. De niet-wijzigbare datum en tijd waarop de publicatie nieuw is toegevoegd.
* ``Laatst gewijzigd op``. De niet-wijzigbare datum en tijd waarop de publicatie voor het laatst gewijzigd was.
* ``Datum begin geldigheid``. De datum waarop de rechten en plichten vastgelegd in deze documenten in werking treden.
*  ``Datum einde geldigheid``. De datum waarop de rechten en plichten vastgelegd in deze documenten (zijn) komen te vervallen.
* ``Eigenaar``. De medewerker die wordt beschouwd als de "eigenaar" van de publicatie. In de GPP-app kan alleen de "eigenaar" de publicatie wijzigen.
* ``Eigenaar (groep)``. De :ref:`organisatie-eenheid <admin_accounts_index_organisation_units>` die ook de publicatie
  mag beheren, naast de medewerker-gebonden eigenaar. De GPP-app laat toe dat andere organisatieleden dan de eigenaar
  de publicatie wijzigen, zolang ze bij deze organisatie-eenheid horen.
* ``UUID``. Een niet-wijzigbaar, automatisch toegekend identificatiekenmerk. (DiWoo: ``identifier``)

**Archivering**

* ``Bron bewaartermijn``. De naam van de bron van de bewaartermijn. Doorgaans zal dit een selectielijst c.q. selectiebesluit zijn, welke conform de vigerende Archiefwet is vastgesteld.
* ``Selectiecategorie``. De specifieke categorie binnen de bron van de bewaartermijn.
* ``Archiefnominatie``. Een radioknop die aangeeft of de publicaties op termijn vernietigd of permanent bewaard moet worden. Permanent te bewaren publicaties moeten conform de vigerende Archiefwet op termijn overgebracht worden naar een archiefbewaarplaats c.q. plusdepot / e-depot.
* ``Archiefactiedatum``. De datum wanneer er actie (vernietiging dan wel overbrenging) genomen moet worden op de *publicatie*.
* ``Toelichting bewaartermijn``. Extra informatie die de (informatie-)beheerder kan aangeven.

Bovenstaande metadata rondom de *bewaartermijn* worden één op één overgenomen van de gekoppelde :ref:`informatiecategorie <admin_metadata_index_information_categories>`, met uitzondering van de ``Archiefactiedatum``.
Deze wordt namelijk berekend door het aantal jaren dat bij de *informatiecategorie* ingevuld is bij ``Bwaartermijn`` op te tellen bij de datum die op de *publicatie* is ingevuld bij ``Geregistreerd op``.

Wanneer meerdere *informatiecategorieën* zijn gekoppeld, dan geldt de langste bewaartermijn; de ``Archiefnominatie`` "bewaren" heeft prioriteit boven "vernietigen" en vervolgens wordt de langste / hoogste ``Bewaartermijn`` gekozen.

Indien gewenst, kunnen de automatisch ingevulde waarden handmatig dan wel via de API overschreven worden.

Te zijner tijd zal de vernietiging dan wel overbrenging geëffectueerd moeten worden.
Onderzocht wordt of hiervoor op termijn aangesloten kan worden op het `Archiefbeheercomponent <https://github.com/maykinmedia/archiefbeheercomponent>`_.
Voorbereidiende gesprekken hierover lopen nog.

.. warning:: De bewaartermijn van de gekoppelde informatiecategorieën wordt toegepast bij het publiceren van een registratie en bij het toevoegen/verwijderen van een koppeling voor de informatiecategorieën. Eventuele manuele aanpassingen op de archiefnominatie, archiefactiedatum en/of overige archiveringsvelden worden hierdoor automatisch overschreven.

.. _Wet open overheid, art. 3.3, lid 8: https://wetten.overheid.nl/BWBR0045754/2024-10-01#Hoofdstuk3_Artikel3.3

.. _admin_publicaties_index_onderwerpen:

Onderwerpen
-----------

Een *onderwerp* bestaat uit een aantal gegevens en omvat geen,een of meerdere :ref:`admin_publicaties_index_publicaties` (zie hierboven).

In het beheerscherm van het *onderwerp* wordt een lijst getoond van alle *onderwerp*-registraties die zijn opgeslagen in de publicatiebank.
Op dit scherm zijn de volgende acties mogelijk:

* Rechtsboven zit een knop **onderwerp toevoegen** waarmee een registratie toegevoegd kan worden.
* Bovenaan zit een zoekveld met een knop **Zoeken** waarmee in de registraties gezocht kan worden.
* Direct onder de zoekbalk zit de mogelijkheid om de lijst te **filteren op een specifieke registratiemaans**.
* Daaronder zit de mogelijkheid om **eenzelfde actie uit te voeren over meerdere onderwerpen**. Op dit moment worden de acties **Geselecteerde onderwerpen verwijderen**, **Verstuur de geselecteerde onderwerpen naar de zoekindex**, **Verwijder de geselecteerde onderwerpen uit de zoekindex** en **Trek gepubliceerde onderwerpen in** ondersteund. Merk op dat het mogelijk is om in de lijst één of meerdere *onderwerp*-registraties aan te vinken.
* Onder de (bulk-)actie staat de lijst met *onderwerp*-registraties. Door op de kolomtitels te klikken kan de lijst **alfabetisch of chronologisch geordend** worden.
* Rechts naast de lijst bestaat de mogelijkheid om deze te **filteren op registratiedatum, publicatiestatus en/of promotie**.
* Bij een *onderwerp*-registratie kan op de `officiële titel` geklikt worden om **de details in te zien** en deze eventueel **te wijzigen**.
* Bij een *onderwerp*-registratie kan op **Toon logs** (rechter kolom) geklikt worden om direct de :ref:`audit trail<admin_logging_index>` in te zien.

Wanneer bij een *onderwerp*-registratie op  de `officiële titel` wordt geklikt, wordt een scherm geopend met de *onderwerp*-details.
Hierop zien we:

* **Alle metadatavelden**. Deze lichten we hieronder toe.
* Rechtsboven een knop **Toon logs**. Deze toont de volledige :ref:`audit trail<admin_logging_index>` van de *onderwerp*-registratie.
* Rechtsboven een knop **Geschiedenis**. Deze toont de beheer-handelingen die vanuit de Admin-interface zijn uitgevoerd op de registratie.
* Onder de metadatavelden staan de gekoppelde *publicaties*. Deze kunnen aangeklikt worden om te openen.
* Linksonder de mogelijkheid om **wijzigingen op te slaan**. Er kan voor gekozen worden om na het opslaan direct een nieuwe registratie aan te maken of om direct de huidige registratie nogmaals te wijzigen.
* Rechtsonder de mogelijkheid om de registratie te **verwijderen**.

Op een *onderwerp*-registratie zijn de volgende metadata beschikbaar. Op het scherm worden verplichte velden **dikgedrukt** weergegeven.

* ``Afbeelding``. De afbeelding van het onderwerp die getoond kan worden in de GPP-burgerportaal.
* ``Officiële titel``. De (mogelijk uitgebreide) officiële titel van het onderwerp.
* ``Omschrijving``. Een beknopte omschrijving / samenvatting van het onderwerp.
* ``Status``. De status van het onderwerp. "Gepubliceerd" betekent dat het onderwerp online vindbaar en raadpleegbaar is. "Ingetrokken" is offline voor de buitenwereld.
* ``Promoot``. Geeft aan of het onderwerp wordt gepromoot in de webapplicatie. Als je gegbruik maakt van het GPP-burgerportaal, dan worden gepromote onderwerpen op de thuispagina en bovenaan op de *onderwerpen*-pagina getoond.
* ``UUID``. Een niet-wijzigbaar, automatisch toegekend identificatiekenmerk.
* ``Geregistreerd op``. De niet-wijzigbare datum en tijd waarop het onderwerp nieuw is toegevoegd.
* ``Laatst gewijzigd op``. De niet-wijzigbare datum en tijd waarop het onderwerp voor het laatst gewijzigd was.
