.. _admin_accounts_index:

Accounts
========

Onder het menu-item "Accounts" en op het dashboard onder het kopje "Accounts" wordt toegang geboden tot het beheer van:

* :ref:`admin_accounts_index_users`
* :ref:`admin_accounts_index_groups`
* :ref:`admin_accounts_index_employees`
* :ref:`admin_accounts_index_organisation_units`
* :ref:`admin_accounts_index_totpdevices`
* :ref:`admin_accounts_index_webauthndevices`

Door hierop te klikken wordt het desbetreffende beheerscherm geopend.

.. _admin_accounts_index_users:

Gebruikers
----------

.. tip:: Als je van Single Sign On (SSO) met OpenID Connect gebruik maakt, dan worden
   de gebruikersaccounts automatisch beheerd.

Beheerscherm
~~~~~~~~~~~~

In het beheerscherm van de gebruikers zie je een lijst van personen die toegang hebben
tot de publicatiebank. Deze lijst toont *alle* gebruikers, ongeacht of je een lokale
gebruikersaccount hebt, of via een organisatie-account inlogt.

Op dit scherm zijn een aantal acties mogelijk:

* Rechtsboven op het beheerscherm zit een knop **Gebruiker toevoegen** waarmee je een
  nieuwe lokale gebruikersaccount kan aanmaken.
* Bovenaan staat een **zoekveld**, waar je gebruikers op gebruikersnaam, voornaam, achternaam
  en e-mailadres kan vinden.
* Er is een bulk-actie om gebruikers te verwijderen, maar het is beter om accounts te
  deactiveren in plaats van verwijderen zodat audit-informatie gekoppeld blijft.
* Rechts kan je **filteren** op een aantal eigenschappen:

    - *Stafstatus ja/nee*: enkel gebruikers met stafstatus kunnen op de beheeromgeving inloggen.
    - *Supergebruikerstatus ja/nee*: supergebruikers hebben altijd alle rechten om alle acties uit te voeren.
    - *Actief ja/nee*: inactieve gebruikers kunnen niet inloggen.
    - *Groepen*: een gebruiker kan lid zijn van één of meerdere :ref:`groepen <admin_accounts_index_groups>` waaraan bepaalde rechten gekoppeld zijn.

* In de lijstweergave kan je voor elke gebruiker :ref:`audit-logs <admin_logging_index>` weergeven via de **Toon logs** link. Deze logs tonen welke wijzigingen er aan het gebruikersaccount gemaakt zijn en door wie.
* De knop **Overnemen** laat (super)gebruikers toe zich voor te doen als de geselecteerde
  gebruiker. Dit is handig om de rechten te controleren of een probleem te reproduceren.

**Gebruiker bewerken**

Wanneer je de gebruikersnaam van een gebruiker aanklikt, dan opent een scherm met
nadere details. Hier zie je:

* **Alle gegevens**. Deze lichten we hieronder toe.
* Rechtsboven een knop **Toon logs**. Deze toont de volledige :ref:`audit trail<admin_logging_index>` van de *gebruiker*.
* Rechtsboven een knop **Geschiedenis**. Deze toont de beheer-handelingen die vanuit de
  beheerinterface zijn uitgevoerd op de *gebruiker*.
* Linksonder de mogelijkheid om de wijzigingen op te slaan. Er kan voor gekozen worden
  om na het opslaan direct een nieuwe registratie aan te maken of om direct de huidige
  registratie nogmaals te wijzigen.
* Rechtsonder de mogelijkheid om de gebruiker te **verwijderen**.

Bij een gebruiker zijn de volgende gegevens beschikbaar. Op het scherm worden verplichte
velden **dikgedrukt** weergegeven.

* ``Gebruikersnaam``. De gebruikersnaam waarmee de gebruiker inlogt. Voor inloggen met
  organisatie-account is dit veelal een technische systeemwaarde.
* ``Wachtwoord``. Gemaskeerde informatie over het gehashte wachtwoord. De wachtwoorden
  zelf zijn nooit te achterhalen.
* ``Persoonlijke gegevens``. Naam en e-mail van de gebruiker.
* ``Actief``. Vlag die aangeeft of de gebruiker kan inloggen.
* ``Stafstatus``. Vlag die aangeeft of de gebruiker kan inloggen op de beheeromgeving.
* ``Supergebruikerstatus``. Vlag die aangeeft of de gebruiker altijd alle rechten heeft.
* ``Groepen``. Je kan gebruikers aan groepen toewijzen zodat ze de rechten van die groep
  krijgen. Dit is aangeraden.
* ``Gebruikersrechten``. Je kan individuele rechten aan gebruikers toekennen, naast of
  in plaats van groepsrechten.

.. warning:: Van supergebruikers wordt verwacht dat ze goed weten wat ze doen, dus ken
   deze rechten alleen toe als het echt noodzakelijk is. Over het algemeen kan je beter
   een gebruiker aan een groep toewijzen.

.. _admin_accounts_index_groups:

Groepen
-------

Groepen bestaan om gebruikersrechten te organiseren.

.. tip:: Als je van Single Sign On (SSO) met OpenID Connect gebruik maakt, dan worden
   sommige groepen automatisch aangemaakt en toegekend aan gebruikers, afhankelijk van
   de OpenID Connect-instellingen.

Beheerscherm
~~~~~~~~~~~~

In het beheerscherm van de groepen zie je een lijst van groepen die bestaan in het
systeem.

.. note:: Een aantal groepen zijn "vastgezet" in de applicatie en wijzigingen aan deze
   groepen worden teruggedraaid bij updates:

   * Technisch beheer
   * Functioneel beheer

Op dit scherm zijn een aantal acties mogelijk:

* Rechtsboven op het beheerscherm zit een knop **Groep toevoegen** waarmee je een
  nieuwe groep kan aanmaken.
* Bovenaan staat een zoekveld, waar je groepen op naam doorzoekt.
* Er is een bulk-actie om groepen te verwijderen.

**Groep bewerken**

Wanneer je de naam van een groep aanklikt, dan opent een scherm met nadere details. Hier
zie je:

* **Alle gegevens**. Deze lichten we hieronder toe.
* Rechtsboven een knop **Geschiedenis**. Deze toont de beheer-handelingen die vanuit de
  beheerinterface zijn uitgevoerd op de *groep*.
* Linksonder de mogelijkheid om de wijzigingen op te slaan. Er kan voor gekozen worden
  om na het opslaan direct een nieuwe registratie aan te maken of om direct de huidige
  registratie nogmaals te wijzigen.
* Rechtsonder de mogelijkheid om de groep te **verwijderen**.

Bij een groep zijn de volgende gegevens beschikbaar. Op het scherm worden verplichte
velden **dikgedrukt** weergegeven.

* ``Naam``. Een unieke naam waaraan je de groep herkent, en waarmee inloggen met
  organisatie-account koppelt voor de groepensynchronisatie.
* ``Rechten``. De mogelijke rechten op objecten die in de beheeromgeving zichtbaar zijn,
  typisch onderverdeeld in *toevoegen*, *wijzigen*, *verwijderen* en *inzien*.

.. _admin_accounts_index_employees:

Organisatieleden
----------------

Een *organisatielid* bevat de minimale velden om een medewerker te kunnen relateren: de
unieke identificatie en de weergavenaam. Organisatieleden zijn eigenaar van publicaties
en documenten. De gegevens worden gevuld via de beheeromgeving of (automatisch) via de
API.

In het beheerscherm van de *organisatieleden* zie je een lijst van alle
*organisatieleden*-registraties. Op dit scherm zijn de volgende acties mogelijk:

* Rechtboven zit een knop **organisatielid toevoegen** waarmee een medewerker toegevoegd
  kan worden.
* Bovenaan zit een zoekveld met een knop **Zoeken** waarmee in de registraties gezocht
  kan worden.
* Daaronder zit de mogelijkheid om **eenzelfde actie uit te voeren over meerdere organisatieleden**.
  Op dit moment wordt de actie **Geselecteerde organisatieleden verwijderen** ondersteund.
  Merk op dat het mogelijk is om in de lijst één of meerdere *organisatielid*-registraties
  aan te vinken.
* Onder de (bulk-)actie staat de lijst met *organisatielid*-registraties. Door op de
  kolomtitels te klikken kan de lijst **alfabetisch geordend** worden.

Wanneer bij een *organisatielid*-registratie op de `identificatie` wordt geklikt, wordt
een scherm geopend met de *medewerker*-details. Hierop zien we:

* **Alle metadatavelden**. Deze lichten we hieronder toe.
* Rechtsboven een knop **Toon logs**. Deze toont de volledige
  :ref:`audit trail<admin_logging_index>` van de *organisatielid*-registratie.
* Rechtsboven een knop **Geschiedenis**. Deze toont de beheerhandelingen die vanuit de
  Admin-interface zijn uitgevoerd op de registratie.
* Linksonder de mogelijkheid om **wijzigingen op te slaan**. Er kan voor gekozen worden
  om na het opslaan direct een nieuwe registratie aan te maken of om direct de huidige
  registratie nogmaals te wijzigen.
* Rechtsonder de mogelijkheid om de registratie te **verwijderen**.

Op een *organisatielid*-registratie zijn de volgende metadata beschikbaar. Op het scherm
worden verplichte velden **dikgedrukt** weergegeven.

* ``Naam``. De weergavenaam van een *organisatielid*.
* ``Identificatie``. Het unieke kenmerk dat intern aan het *organisatielid* is toegekend.
  Deze kan je niet wijzigen voor bestaande objecten. De waarde moet uit de
  inlog-voorziening van de organisatie komen.

.. _admin_accounts_index_organisation_units:

Organisatie-eenheden
--------------------

Een *organisatie-eenheid* bevat de minimale velden om een organisatie-eenheid te kunnen
relateren: de unieke identificatie en de weergavenaam. Organisatie-eenheden kunnen (ook)
eigenaar zijn van publicaties en documenten, naast het organisatielid. De gegevens
worden gevuld via de beheeromgeving of (automatisch) via de API.

In het beheerscherm van de *organisatie-eenheden* zie je een lijst van alle
*organisatie-eenheden*-registraties. Op dit scherm zijn de volgende acties mogelijk:

* Rechtboven zit een knop **organisatie-eenheid toevoegen** waarmee een groep toegevoegd
  kan worden.
* Bovenaan zit een zoekveld met een knop **Zoeken** waarmee in de registraties gezocht
  kan worden.
* Daaronder zit de mogelijkheid om **eenzelfde actie uit te voeren over meerdere organisatie-eenheden**.
  Op dit moment wordt de actie **Geselecteerde organisatie-eenheden verwijderen** ondersteund.
  Merk op dat het mogelijk is om in de lijst één of meerdere *organisatie-eenheid*-registraties
  aan te vinken.
* Onder de (bulk-)actie staat de lijst met *organisatie-eenheid*-registraties. Door op de
  kolomtitels te klikken kan de lijst **alfabetisch geordend** worden.

Wanneer bij een *organisatie-eenheid*-registratie op de `identificatie` wordt geklikt, wordt
een scherm geopend met de *medewerker*-details. Hierop zien we:

* **Alle metadatavelden**. Deze lichten we hieronder toe.
* Rechtsboven een knop **Toon logs**. Deze toont de volledige
  :ref:`audit trail<admin_logging_index>` van de *organisatie-eenheid*-registratie.
* Rechtsboven een knop **Geschiedenis**. Deze toont de beheerhandelingen die vanuit de
  Admin-interface zijn uitgevoerd op de registratie.
* Linksonder de mogelijkheid om **wijzigingen op te slaan**. Er kan voor gekozen worden
  om na het opslaan direct een nieuwe registratie aan te maken of om direct de huidige
  registratie nogmaals te wijzigen.
* Rechtsonder de mogelijkheid om de registratie te **verwijderen**.

Op een *organisatie-eenheid*-registratie zijn de volgende metadata beschikbaar. Op het scherm
worden verplichte velden **dikgedrukt** weergegeven.

* ``Naam``. De weergavenaam van een *organisatie-eenheid*.
* ``Identificatie``. Het unieke kenmerk dat intern aan het *organisatie-eenheid* is toegekend.
  Deze kan je niet wijzigen voor bestaande objecten. De waarde wordt typisch aangelever
  door de GPP-app via de API.

.. _admin_accounts_index_totpdevices:

TOTP devices
------------

.. warning:: Dit onderdeel behoort tot de geavanceerde/technische functies. Maak hier
   enkel wijzingen als je weet wat je doet.

TOTP-devices zijn een onderdeel van de functionaliteiten voor
multi-factor-authenticatie (MFA). Het bevat de technische gegevens voor gebruikers om
een éénmalige code te kunnen generen bij het inloggen met lokale gebruikersaccounts.

We documenteren deze functionaliteit verder niet.

.. _admin_accounts_index_webauthndevices:

Webauthn devices
----------------

.. warning:: Dit onderdeel behoort tot de geavanceerde/technische functies. Maak hier
   enkel wijzingen als je weet wat je doet.

Webauthn devices zijn een onderdeel van de functionaliteiten voor
multi-factor-authenticatie (MFA). Het bevat de technische gegevens voor gebruikers om
bij het inloggen met lokale gebruikersaccounts een hardware token te gebruiken in plaats
van een éénmalige code.

We documenteren deze functionaliteit verder niet.
