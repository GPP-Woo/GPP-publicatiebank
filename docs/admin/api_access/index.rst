.. _admin_api_access_index:

API-toegang
===========

Onder het menu-item "API-toegang" en op het dashboard onder het kopje "API-toegang"
beheer je "Applicatie-API-Keys".

Door hierop te klikken wordt het desbetreffende beheerscherm geopend.

.. _admin_api_access_index_apikeys:

Applicatie-API-Keys
-------------------

Toelichting
~~~~~~~~~~~

De GPP-Publicatiebank biedt een API aan voor andere applicaties (zoals de GPP-App) om
te koppelen. Hiermee kunnen publicaties beheerd en opgehaald worden. Dergelijke APIs
dienen beveiligd te worden zodat enkel bedoelde applicaties toegang hebben, ook als
het openbare publicaties betreft.

In de GPP-Publicatiebank kan je applicaties registreren met een toegangssleutel zodat je
de API-toegang kan controleren.

.. tip:: Behandel de toegangssleutels als wachtwoorden - je hebt enkel deze sleutel
   nodig om toegang te krijgen tot de API.

Beheerscherm
~~~~~~~~~~~~

In het beheerscherm van de applicatie-API-keys zie je een lijst van applicaties die
toegang hebben. De contactgegevens (indien bekend) worden afgebeeld.

De eerste kolom bevat de API-key zelf - deze moet je instellen bij de applicatie die
wenst te koppelen met de GPP-Publicatiebank.

Op het beheerscherm zijn de volgende acties mogelijk:

* Rechtboven zit een knop **applicatie-api-key toevoegen** waarmee je een (nieuwe)
  applicatie toegang kan geven.
* Er is een bulk-actie om API-sleutels te verwijderen. Hiermee wordt onmiddellijk de
  toegang ingetrokken.

**API-key bewerken**

Wanneer je het token aanklikt, dan opent een scherm met nadere details. Hier zie je:

* **Alle gegevens**. Deze lichten we hieronder toe.
* Rechtsboven een knop **Toon logs**. Deze toont de volledige
  :ref:`audit trail<admin_logging_index>` van de *applicatie-API-key*.
* Rechtsboven een knop **Geschiedenis**. Deze toont de beheer-handelingen die vanuit de
  beheerinterface zijn uitgevoerd op de *applicatie-API-key*.
* Linksonder de mogelijkheid om de wijzigingen op te slaan.
* Rechtsonder de mogelijkheid om de applicatie-API-key te **verwijderen**. Hiermee wordt
  onmiddellijk de toegang ingetrokken.

De volgende gegevens zijn beschikbaar. Op het scherm worden verplichte
velden **dikgedrukt** weergegeven.

* ``Rechten``. Een applicatie kan lees- en/of schrijfrechten hebben. Met leesrechten
  kunnen enkel gegevens opgevraagd worden, met schrijfrechten kunnen ze ook bijgewerkt
  worden en nieuwe gegevens aangemaakt worden. Een GPP-App heeft beide nodig, een
  GPP-Burgerportaal heeft enkel leesrechten nodig.
* ``Contactpersoon``. Naam van de contactpersoon voor de applicatie die koppelt met
  GPP-Publicatiebank.
* ``E-mail``. E-mailadres van de contactpersoon.
* ``Telefoonnummer``. Telefoonnummer van de contactpersoon.
* ``Token``. De API-key zelf. Deze wordt gegenereerd bij het aanmaken van de
  applicatie-API-key.

Wat te doen als een API-key onbedoeld uitlekt?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Het kan gebeuren dat de waarde van het token/de API-sleutel onbedoeld publiek gemaakt
wordt. Het is belangrijk om dan zo snel mogelijk misbruik te voorkomen:

**Als je de gebruiker bent van de API-key**

Neem contact op met de beheerders van de GPP-Publicatiebank. Vermeld hierbij om welk
token het gaat, en vanaf welk moment dat deze niet meer veilig was. Je krijgt nadere
instructies van de GPP-publicatiebankbeheerder.

**Als je beheerder bent van de GPP-publicatiebank**

De volgorde van de acties is afhankelijk of je door de gebruiker van de API-key
geïnformeerd bent of niet. Stem in ieder geval af met je contactpersoon! Zorg dat je
weet (of een schatting hebt) wanneer de API-key gelekt is, zodat je hiermee logs kan
analyseren.

* Navigeer in de beheeromgeving naar **API-toegang** > **Applicatie-API-keys**
* Klik de gelekte API key aan om de details te openen
* Verwijder de rechten door op de kruisjes te klikken, en sla de gegevens op met
  "Opslaan en opnieuw bewerken".
* Neem contact op met de tegenpartij en informeer hen van de situatie/ondernomen acties.

Het intrekken van de rechten zorgt ervoor dat er geen misbruik meer (kan) gemaakt
worden.

* Controleer de audit-logs om te achterhalen of er misbruik gemaakt is. Navigeer
  hiervoor naar **Logging** > **(audit)log items**.
* Het is vooral interessant om logs te analyseren vanaf het tijdstip dat de API-key
  gelekt is.

Als er geen verdachte acties in de logs te zien zijn, dan kan je een nieuwe
applicatie-API-key aanmaken en het nieuwe token terugcommuniceren naar de gebruiker van
de API.
