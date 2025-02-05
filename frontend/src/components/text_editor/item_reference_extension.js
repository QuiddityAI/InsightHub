import { mergeAttributes, Node } from '@tiptap/core'
import { VueNodeViewRenderer } from '@tiptap/vue-3'

import ItemReferenceInline from './ItemReferenceInline.vue'


export default Node.create({
  name: 'itemReference',
  group: "inline",
  content: "inline*",
  atom: true,
  inline: true,

  addAttributes() {
    return {
      dataset_id: {
        default: 0,
      },
      item_id: {
        default: "foo",
      },
      reference_idx: {
        default: "1",
      },
      reference_title: {
        default: "baz",
      },
    }
  },

  parseHTML() {
    return [
      {
        tag: 'item-reference',
      },
    ]
  },

  renderHTML({ HTMLAttributes }) {
    return ['item-reference', mergeAttributes(HTMLAttributes)]
  },

  addNodeView() {
    return VueNodeViewRenderer(ItemReferenceInline)
  },
})
