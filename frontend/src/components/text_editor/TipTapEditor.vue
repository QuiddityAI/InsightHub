<script setup>
import StarterKit from '@tiptap/starter-kit'
import { Editor, EditorContent } from '@tiptap/vue-3'
import { TableKit } from '@tiptap/extension-table'
import TurndownService from 'turndown'
import { marked } from "marked";
import { Placeholder } from '@tiptap/extensions'

import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"

import ItemReferenceExtension from './item_reference_extension.js'
import { tables } from 'joplin-turndown-plugin-gfm'
import { httpClient } from "../../api/httpClient"



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
      showPopup: false, // State for popup visibility
    };
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
    },
    async exportMarkdown() {
      const markdownContent = this.modelValue;

      // Replace references with actual names
      const regex = /\[([0-9]+),\s([0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12})\]/g;
      let match;
      let updatedMarkdown = markdownContent;

      while ((match = regex.exec(markdownContent)) !== null) {
        const dataset_id = match[1];
        const item_id = match[2];

        try {
          // Fetch the item details (simulate API call or use existing data)
          const response = await httpClient.post("/data_backend/document/details_by_id", {
            dataset_id,
            item_id,
            fields: ["title"], // Assuming "title" is the field containing the reference title
          });

          const itemTitle = response.data.title || "[Unknown Reference]";
          updatedMarkdown = updatedMarkdown.replace(match[0], itemTitle);
        } catch (error) {
          console.error(`Failed to fetch details for [${dataset_id}, ${item_id}]`, error);
          updatedMarkdown = updatedMarkdown.replace(match[0], "[Error Fetching Reference]");
        }
      }

      // Export the updated markdown
      const blob = new Blob([updatedMarkdown], { type: 'text/markdown;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'summary.md';
      link.click();
      URL.revokeObjectURL(url);
    },
    async copyInnerHtml() {
      const htmlContent = this.editor.getHTML();

      // Replace references with actual names
      const regex = /<item-reference dataset_id="([0-9]+)" item_id="([0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12})" reference_idx="([0-9]+)" reference_title="([^"]+)"><\/item-reference>/g;
      let match;
      let updatedHtmlContent = htmlContent;

      while ((match = regex.exec(htmlContent)) !== null) {
        const dataset_id = match[1];
        const item_id = match[2];

        try {
          // Fetch the item details (simulate API call or use existing data)
          const response = await httpClient.post("/data_backend/document/details_by_id", {
            dataset_id,
            item_id,
            fields: ["title"], // Assuming "title" is the field containing the reference title
          });

          const itemTitle = `[${response.data.title || "Unknown Reference"}]`;
          updatedHtmlContent = updatedHtmlContent.replace(match[0], itemTitle);
        } catch (error) {
          console.error(`Failed to fetch details for [${dataset_id}, ${item_id}]`, error);
          updatedHtmlContent = updatedHtmlContent.replace(match[0], "[Error Fetching Reference]");
        }
      }

      try {
        const blob = new Blob([updatedHtmlContent], { type: 'text/html' });
        const clipboardItem = new ClipboardItem({ 'text/html': blob });
        await navigator.clipboard.write([clipboardItem]);
        console.log('Rich text content copied to clipboard');
        this.showPopup = true; // Show popup
        setTimeout(() => {
          this.showPopup = false; // Hide popup after 2 seconds
        }, 2000);
      } catch (err) {
        console.error('Could not copy text: ', err);
      }
    },
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
        TableKit,
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
        const turndownService = new TurndownService({ 'headingStyle': 'atx' }).use(tables)
        const markdown = turndownService.turndown(text)
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
  <editor-content :editor="editor" class="use-default-html-styles use-default-html-styles-large text-[14px]"
    spellcheck="false" />
  <div class="flex gap-2 mt-2">
    <button @click="exportMarkdown" class="export-button">Download</button>
    <button @click="copyInnerHtml" class="export-button">Copy to clipboard</button>
  </div>
  <div v-if="showPopup" class="popup-notification">Copied to clipboard!</div>
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

.export-button {
  margin-top: 0.1rem;
  padding: 0.25rem 0.5rem;
  background-color: white;
  color: var(--black);
  border: 1px solid gray;
  /* Thin gray outline */
  border-radius: 0.25rem;
  cursor: pointer;
  font-size: 0.75rem;
}

.export-button:hover {
  background-color: var(--gray-2);
  border-color: var(--gray-3);
}

.popup-notification {
  position: fixed;
  bottom: 20px;
  right: 20px;
  background-color: #4caf50;
  color: white;
  padding: 10px 20px;
  border-radius: 5px;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2);
  z-index: 1000;
  animation: fadeInOut 2.5s;
}

@keyframes fadeInOut {

  0%,
  100% {
    opacity: 0;
  }

  10%,
  90% {
    opacity: 1;
  }
}
</style>
