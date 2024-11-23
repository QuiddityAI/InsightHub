<script setup>
import { nodeViewProps, NodeViewWrapper } from '@tiptap/vue-3'

import OverlayPanel from "primevue/overlaypanel";

import ReferenceHoverInfo from '../collections/ReferenceHoverInfo.vue'

import { useAppStateStore } from "../../stores/app_state_store"

const appState = useAppStateStore()


</script>

<script>

export default {
  props: nodeViewProps,

  data() {
    return {
    }
  },

  methods: {
    handleMouseEnter(event) {
      this.$refs.reference_tooltip.show(event)
    },

    handleMouseLeave() {
      this.$refs.reference_tooltip.hide()
    },
  },
}
</script>

<template>
  <NodeViewWrapper class="hover:text-blue-500 inline">

    <span
      @mouseenter="handleMouseEnter"
      @mouseleave="handleMouseLeave"
      @click="appState.show_document_details([node.attrs.dataset_id, node.attrs.item_id])"
      class="cursor-pointer">
      [{{ node.attrs.reference_idx }}]
    </span>

    <OverlayPanel ref="reference_tooltip" class="absolute z-10">
      <ReferenceHoverInfo
        class="w-[500px]"
        :dataset_id="node.attrs.dataset_id"
        :item_id="node.attrs.item_id">
      </ReferenceHoverInfo>
    </OverlayPanel>

  </NodeViewWrapper>
</template>