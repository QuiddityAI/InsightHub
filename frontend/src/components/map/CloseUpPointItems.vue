<script setup>
import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useMapStateStore } from "../../stores/map_state_store"
const appState = useAppStateStore()
const mapState = useMapStateStore()
</script>

<script>


export default {
  inject: ["eventBus"],
  emits: [],
  data() {
    return {
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
  },
  mounted() {
  },
  watch: {
  },
  methods: {
  },
}
</script>

<template>
  <div class="pointer-events-none">

    <div
      class="pointer-events-none absolute transition-opacity duration-300"
      :class="{'opacity-0': !mapState.show_html_points, 'opacity-100': mapState.show_html_points}">
      <div
        v-for="pointIndex in mapState.visiblePointIndexes"
        :key="pointIndex"
        class="pointer-events-none absolute"
        :style="{
          left: mapState.screenLeftFromRelative(mapState.per_point.x[pointIndex]) - 220 + 'px',
          bottom: mapState.screenBottomFromRelative(mapState.per_point.y[pointIndex]) + 'px',
        }"
        style="transform: translate(0%, 50%)">
        <button
          v-if="appState.get_hover_rendering_by_index(pointIndex) && mapState.hovered_point_idx !== pointIndex"
          @click="appState.show_document_details(mapState.per_point.item_id[pointIndex])"
          class="flex max-w-[200px] flex-col rounded bg-white px-2 py-1 text-[10px] text-gray-500 hover:bg-gray-100 text-left"
          :class="{'pointer-events-auto': mapState.show_html_points}">
          <div
            class="text-xs font-semibold"
            v-html="appState.get_hover_rendering_by_index(pointIndex).title(mapState.get_item_by_index(pointIndex))">
          </div>
          <div
            class="mt-1 text-xs font-normal"
            v-show="appState.get_hover_rendering_by_index(pointIndex).subtitle(mapState.get_item_by_index(pointIndex))"
            v-html="appState.get_hover_rendering_by_index(pointIndex).subtitle(mapState.get_item_by_index(pointIndex))">
          </div>
          <img
            v-if="appState.get_hover_rendering_by_index(pointIndex).image(mapState.get_item_by_index(pointIndex))"
            :src="appState.get_hover_rendering_by_index(pointIndex).image(mapState.get_item_by_index(pointIndex))"
            class="h-24" />
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped></style>
