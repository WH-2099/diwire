.. meta::
   :description: diwire annotation normalization examples: non-component Annotated metadata is stripped from dependency keys.

Annotation normalization
========================

What you'll learn
-----------------

- ``Annotated[T, <non-component-meta>]`` resolves the same as ``T``.
- ``Annotated[T, Component("name"), <non-component-meta>]`` resolves the same as
  ``Annotated[T, Component("name")]``.

Registration and resolve key normalization
------------------------------------------

Run locally
~~~~~~~~~~~

.. code-block:: bash

   uv run python examples/ex_24_annotation_normalization/01_registration_keys.py

.. literalinclude:: ../../../examples/ex_24_annotation_normalization/01_registration_keys.py
   :language: python
   :class: diwire-example py-run

Non-component metadata normalization
------------------------------------

Run locally
~~~~~~~~~~~

.. code-block:: bash

   uv run python examples/ex_24_annotation_normalization/02_non_component_metadata_keys.py

.. literalinclude:: ../../../examples/ex_24_annotation_normalization/02_non_component_metadata_keys.py
   :language: python
   :class: diwire-example py-run
