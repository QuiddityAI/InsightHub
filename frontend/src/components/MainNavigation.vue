<script setup>
import SearchAndMap from './SearchAndMap.vue';

import { useAppStateStore } from '../stores/settings_store'

const appState = useAppStateStore()
</script>

<script>

export default {
  data() {
    return {
    }
  },
  methods: {

  }
}

</script>

<template>
  <div class="min-h-full">
    <SearchAndMap/>
    <div v-if="appState.dataset ? !appState.dataset.workspace_tool_title : true" class="absolute bottom-4 -right-3 pl-3 pr-5 py-1 bg-black rounded-xl shadow-sm font-['Lexend']">
      <span class="text-white font-bold">Quiddity</span> <span class="text-gray-200 font-light">Workspace</span>
    </div>
  </div>
</template>

<style scoped></style>
