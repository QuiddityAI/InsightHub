<script setup>
import {
  HomeIcon,
  UserCircleIcon,
} from "@heroicons/vue/24/outline"

import OverlayPanel from 'primevue/overlaypanel';

import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"

const appState = useAppStateStore()
</script>

<script>

export default {
  inject: ["eventBus"],
  props: [],
  emits: [],
  data() {
    return {
    }
  },
  computed: {
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

  <div class="bg-white rounded-lg shadow-md px-7 py-7 flex flex-col gap-5 text-gray-800">

    <div class="flex flex-row items-center gap-5">
      <img class="h-6" :src="appState.organization.tool_logo_url" />
      <h3 class="ml-3 text-2xl font-medium text-gray-700 font-['Lexend']">{{ appState.organization.tool_title }}</h3>
    </div>

    <div class="-mx-1 -mt-2 border-t-2" :style="`border-color: ${appState.organization.tool_accent_color};`"></div>

    <div class="use-default-html-styles" v-html="appState.organization.tool_intro_text"></div>
  </div>

</template>

<style scoped>
</style>