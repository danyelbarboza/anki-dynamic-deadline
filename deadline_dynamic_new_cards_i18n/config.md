# Dynamic Deadline New Cards

This add-on automatically adjusts the daily new card limit of decks with a configured deadline.

## What it changes

It changes the selected deck's **Daily Limits > New cards/day > This deck** field.

It **does not** create a new preset and **does not** rename presets.

## Language

The default language is English.

You can change the interface language in:

**Tools > Dynamic Deadline: Configure... > Language**

Available languages:

- English
- Português

The selected language is saved in the add-on configuration as:

```json
"language": "en"
```

or:

```json
"language": "pt_BR"
```

## Margin above/below exact pace

The configuration window includes the field **Margin above/below exact pace**:

- `0%`: exact pace to clear the deck by the deadline.
- `+20%`: do 20% more than the exact pace, likely finishing earlier.
- `-10%`: do 10% less than the exact pace, likely finishing later.

The preview shows:

- how many new cards remain;
- the exact pace in cards/day;
- the daily limit that will be saved in **This deck**;
- the approximate estimated completion date.

## Advanced settings

- `decks`: saved deck-specific settings. Normally edit this through Tools > Dynamic Deadline.
- `language`: `en` or `pt_BR`. Default: `en`.
- `daily_adjustment_percent`: saved per deck when you use the margin field.
- `rounding`: `ceil`, `round`, or `floor`. Default: `ceil`, to avoid leaving cards behind at the deadline.
- `minimum_new_per_day`: minimum number of new cards per day when new cards still exist.
- `show_tooltips_on_auto_update`: if `true`, shows a discreet tooltip when automatic recalculation runs.

## Note

If you used an older version of this add-on that created a preset named `Deadline Auto - ...`, this version no longer creates presets. You can manually move the deck back to your preferred preset in Deck Options.

---

# Deadline Dinâmico - Novos por Dia

Este add-on ajusta automaticamente o limite de cards novos por dia de baralhos com deadline configurado.

## O que ele altera

Ele altera o campo **Limites Diários > Novos cartões/dia > Esse baralho** do baralho selecionado.

Ele **não** cria preset novo e **não** renomeia preset.

## Idioma

O idioma padrão é inglês.

Você pode mudar o idioma da interface em:

**Ferramentas > Dynamic Deadline: Configure... > Language**

Idiomas disponíveis:

- English
- Português
