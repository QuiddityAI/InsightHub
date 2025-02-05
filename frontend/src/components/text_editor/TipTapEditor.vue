<script setup>
import StarterKit from '@tiptap/starter-kit'
import Placeholder from '@tiptap/extension-placeholder'
import { Editor, EditorContent } from '@tiptap/vue-3'
import TurndownService from 'turndown'
import {marked} from "marked";

import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"

import ItemReferenceExtension from './item_reference_extension.js'

const appState = useAppStateStore()


TurndownService.prototype.escape = function (string) {
  return string
}

</script>

<script>

export default {
  components: {
    EditorContent,
  },

  props: {
    modelValue: {
      type: String,
      default: '',
    },
    reference_order: null,
  },

  emits: ['update:modelValue', 'change'],

  computed: {
    ...mapStores(useAppStateStore),
  },

  data() {
    return {
      editor: null,
      last_user_change: new Date(),
    }
  },

  methods: {
    markdownToHtml(markdown) {
      if (!markdown) {
        return ''
      }
      let text = markdown

      // replace references in the style [datset_id, item_id] with <item-reference> components:
      const regex = /\[([0-9]+),\s([0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12})\]/g
      let match
      while ((match = regex.exec(text)) !== null) {
        try {
          const dataset_id = match[1]
          const item_id = match[2]
          console.log(dataset_id, item_id, this.reference_order)
          const idx = this.reference_order.findIndex(([d, i]) => d.toString() === dataset_id && i === item_id) + 1
          const replacement = `<item-reference dataset_id="${dataset_id}" item_id="${item_id}" reference_idx="${idx}"></item-reference>`;
          text = text.replace(match[0], replacement);
        } catch (error) {
          console.error(error)
          text = text.replace(match[0], `[?]`);
        }
      }
      const html = marked.parse(text)
      return html
    }
  },

  watch: {
    modelValue(markdown) {
      if (new Date() - this.last_user_change < 200) {
        // don't update the editor content if the change was just made by the user
        return
      }
      const html = this.markdownToHtml(markdown)
      const isSame = this.editor.getHTML() === html
      if (isSame) {
        return
      }
      this.editor.commands.setContent(html, false)
    },
  },

  mounted() {
    this.editor = new Editor({
      extensions: [
        StarterKit,
        Placeholder.configure({
          placeholder: 'No text yet …',
        }),
        ItemReferenceExtension,
      ],
      content: this.markdownToHtml(this.modelValue),
      onUpdate: () => {
        const html = this.editor.getHTML()

        // replace <item-reference> components with [datset_id, item_id] references:
        const regex = /<item-reference dataset_id="([0-9]+)" item_id="([0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12})" reference_idx="([0-9]+)" reference_title="([^"]+)"><\/item-reference>/g;
        let match;
        let text = html
        while ((match = regex.exec(html)) !== null) {
          const replacement = `[${match[1]}, ${match[2]}]`;
          text = text.replace(match[0], replacement);
        }
        const markdown = new TurndownService({'headingStyle': 'atx'}).turndown(text)
        this.last_user_change = new Date()
        this.$emit('update:modelValue', markdown)
        this.$emit('change')
      },
    })
  },

  beforeUnmount() {
    this.editor.destroy()
  },
}
</script>

<template>
  <editor-content :editor="editor" class="use-default-html-styles use-default-html-styles-large text-[14px]" spellcheck="false" />
</template>

<style lang="scss">
/* Basic editor styles */

.ProseMirror:focus {
    outline: none;
}

.tiptap {

  :first-child {
    margin-top: 0;
  }

  /* List styles */
  ul,
  ol {
    padding: 0 1rem;
    margin: 1.25rem 1rem 1.25rem 0.4rem;

    li p {
      margin-top: 0.25em;
      margin-bottom: 0.25em;
    }
  }

  /* Heading styles */
  h1,
  h2,
  h3,
  h4,
  h5,
  h6 {
    line-height: 1.1;
    margin-top: 2.5rem;
    text-wrap: pretty;
  }

  h1,
  h2 {
    margin-top: 3.5rem;
    margin-bottom: 1.5rem;
  }

  h1 {
    font-size: 1.4rem;
  }

  h2 {
    font-size: 1.2rem;
  }

  h3 {
    font-size: 1.1rem;
  }

  h4,
  h5,
  h6 {
    font-size: 1rem;
  }

  /* Code and preformatted text styles */
  code {
    background-color: var(--purple-light);
    border-radius: 0.4rem;
    color: var(--black);
    font-size: 0.85rem;
    padding: 0.25em 0.3em;
  }

  pre {
    background: var(--black);
    border-radius: 0.5rem;
    color: var(--white);
    font-family: 'JetBrainsMono', monospace;
    margin: 1.5rem 0;
    padding: 0.75rem 1rem;

    code {
      background: none;
      color: inherit;
      font-size: 0.8rem;
      padding: 0;
    }
  }

  blockquote {
    border-left: 3px solid var(--gray-3);
    margin: 1.5rem 0;
    padding-left: 1rem;
  }

  hr {
    border: none;
    border-top: 1px solid var(--gray-2);
    margin: 2rem 0;
  }

  /* Placeholder (at the top) */
  p.is-editor-empty:first-child::before {
    color: gray;
    content: attr(data-placeholder);
    float: left;
    height: 0;
    pointer-events: none;
  }
}
</style>
