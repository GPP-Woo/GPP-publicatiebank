.. _`Wet open overheid (Woo)` : https://wetten.overheid.nl/BWBR0045754/
.. _`Common Ground`: https://commonground.nl/

GPP-Publicatiebank
==================

The Dutch government wishes to be open and transparent to its citizens. To achieve this,
the law `Wet open overheid (Woo)`_ was established, 
requiring government organisations to actively and digitally publish their documents and thus create *public records*.

To support govenment organisations in executing this law, the "Generic Publications Platform Woo (GPP-Woo)" was developed. 
This platform is an aggregation of four components, including the 'GPP-Publicatiebank' component.
This component provides a storage repository and JSON API to manage and expose public records including their metadata.

For a full publication platform, three additional components are required:

* `GPP App <https://github.com/GPP-Woo/GPP-app>`_, a component which provides public servants with a web-based user interface to manulaly upload and publish public records.
* `GPP Search <https://github.com/GPP-Woo/GPP-zoeken>`_, a component responsible for indexing public records.
* `GPP Citizen Portal <https://github.com/GPP-Woo/GPP-burgerportaal>`_, a component which provides citizens with a website where they can browse and search through public records.

All components are designed in line with the `Common Ground`_ model.

This project is and only uses :ref:`introduction_open-source`.

Getting started
---------------

To get you started, you might find some of these links relevant:

* New to this project? Have a look at the :ref:`introduction_index`.
* New to the API? Read up on the :ref:`api_index`.
* Want to get started now? See the :ref:`installation reference <installation_index>`.
* Want to know how the admin interface works? Go to the :ref:`admin_index`.
* Want to integrate your third party software? See :ref:`developers_automated_publishing`.


.. toctree::
   :maxdepth: 2
   :hidden:

   introduction/index
   api/index
   admin/index
   installation/index
   configuration/index
   developers/index
   versions
   changelog
